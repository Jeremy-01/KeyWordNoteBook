# Copyright (c) 2025 Y.MF
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

"""
密码管理核心
实现文件管理，词条加密、存储功能
提供增、删、改、查的API函数
"""
__version__ = "0.0.2.1"

import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from datetime import datetime

from argon2 import PasswordHasher, exceptions, Type
from cryptography.fernet import Fernet


logger = logging.getLogger(__name__)


class PasswordNotebookError(Exception):
    """密码本业务异常基类。"""


class InvalidPasswordError(PasswordNotebookError):
    """主密码错误。"""


class IntegrityError(PasswordNotebookError):
    """文件完整性校验失败。"""


def is_base64(s: str) -> bool:
    """验证字符串是否为Base64编码的字符串"""
    try:
        decoded = base64.b64decode(s, validate=True)
        return base64.b64encode(decoded) == s.encode()
    except (binascii.Error, ValueError):
        return False

class Argon2Params(dict):
    """ARGON2算法参数"""
    keycode = {
        "kdf_version": lambda x: isinstance(x, int) and x >= 1,                     # KDF版本
        "verify_hash": lambda x:isinstance(x,str) and x.startswith("$argon2id$"),   # 验证哈希数
        "hash_len": lambda x:isinstance(x,int) and x >= 64,                         # 哈希结果长度
        "encryption_salt": lambda x:isinstance(x,str) and is_base64(x),             # AES加密盐
        "hmac_salt": lambda x: isinstance(x, str) and is_base64(x),                 # HMAC盐
        "hmac_key_encrypted":lambda x:isinstance(x,str),                            # 加密存储HMAC密钥
        "integrity_check": lambda x: isinstance(x, str) and len(x) == 64            # HMAC完整性校验值
    }
    def __setitem__(self, key, value):
        if key not in self.keycode:
            raise KeyError(f"不允许的键: {key}")
        if not self.keycode[key](value):
            raise ValueError(f"键 {key} 的值 {value} 不符合要求")
        super().__setitem__(key, value)
    def update(self, *args, **kwargs):
        temp_dict = dict(*args, **kwargs)
        for key, value in temp_dict.items():
            self[key] = value

class KeyItem(dict):
    """用户条目声明"""
    keycode = {
        # 由管理器控制和获取
        "Index": lambda x:isinstance(x,str),            # 条目序号，唯一ID
        "PasswordLevel": lambda x: isinstance(x, int),  # 密码等级
        "LastUsedAt": lambda x: isinstance(x, str),     # 最近使用时间
        "UpdatedAt": lambda x: isinstance(x, str),      # 最后修改时间
        # 由用户填写
        "URL": lambda x:isinstance(x,str),              # 使用的网址
        "UserName": lambda x:isinstance(x,str),         # 用户名
        "Password": lambda x:isinstance(x,str),         # 密码，在文件中使用密文储存
        "LinkURL": lambda x:isinstance(x,str),          # 关联账户
        "Note": lambda x:isinstance(x,str)              # 备注
    }
    def __setitem__(self, key, value):
        if key not in self.keycode:
            raise KeyError(f"不允许的键: {key}")
        if not self.keycode[key](value):
            raise ValueError(f"键 {key} 的值 {value} 不符合要求")
        super().__setitem__(key, value)
    def update(self, *args, **kwargs):
        temp_dict = dict(*args, **kwargs)
        for key, value in temp_dict.items():
            self[key] = value

class FrequentlyKey(dict):
    """常用密码条目"""
    keycode = {
        "Password": lambda x:isinstance(x,str),         # 密码，在文件中使用密文储存
        "PasswordLevel": lambda x: isinstance(x, int),  # 密码等级
        "Note": lambda x: isinstance(x, str)  # 备注
    }
    def __setitem__(self, key, value):
        if key not in self.keycode:
            raise KeyError(f"不允许的键: {key}")
        if not self.keycode[key](value):
            raise ValueError(f"键 {key} 的值 {value} 不符合要求")
        super().__setitem__(key, value)
    def update(self, *args, **kwargs):
        temp_dict = dict(*args, **kwargs)
        for key, value in temp_dict.items():
            self[key] = value

class PasswordNotebook:
    """密码本管理器"""
    KDF_VERSION_LEGACY = 1
    KDF_VERSION_CURRENT = 2

    def __init__(self, main_key: str, path: str = r"my_key.json"):
        """
        :param mainKey: 管理员主密钥
        :param path: 密码本文件路径
        """
        self.path = path
        self.main_key = main_key
        self.book_data: dict = {}
        self.verify_hash = None
        self.kdf_version = self.KDF_VERSION_CURRENT
        self.encryption_salt = None
        self.hmac_salt = None
        self.hmac_key = None
        self._deferred_sync_dirty = False
        self._password_hash_to_item_ids: dict[str, set[str]] = {}
        self._item_id_to_password_hash: dict[str, str] = {}
        self._duplicate_index_ready = False
        self._duplicate_index_dirty = False
        self._aes_key_cache: bytes | None = None
        self._fernet_cache: Fernet | None = None
        self._pending_v2_strong_migration = False

        self.verify_hasher = PasswordHasher(
            type=Type.ID,
            memory_cost=131072,
            time_cost=6,
            parallelism=6,
            hash_len=64)

        # 会话内派生（v2）：与认证保持同强度，优先保证离线抗暴力能力
        self.session_hasher = PasswordHasher(
            type=Type.ID,
            memory_cost=131072,
            time_cost=6,
            parallelism=6,
            hash_len=64)

        # 兼容历史v2（旧轻参数）读取与迁移使用
        self.legacy_session_hasher = PasswordHasher(
            type=Type.ID,
            memory_cost=65536,
            time_cost=3,
            parallelism=4,
            hash_len=64)

        self._init_or_load_file()

    # API函数
    def verify_master_key(self, user_password: str) -> bool:
        """
        验证用户权限
        :param user_password: 二级密码
        """
        is_verified = self._verify_password(user_password)
        if is_verified:
            logger.debug("主密码验证成功")
        else:
            logger.warning("主密码验证失败")
        return is_verified

    def create_item(self, data: KeyItem, user_password: str) -> str:
        """
        向文件中新增条目，主键自增
        :param data:要添加的条目
        :param user_password: 二级密码
        :return:新增条目的key
        """
        if not self._authorize_action(user_password, "添加条目"):
            return "-1"

        item_data = data
        item_data["Index"] = self._get_index()
        item_data["PasswordLevel"] = self.get_password_level(item_data["Password"])
        plain_password = item_data["Password"]
        password_hash = self._password_plain_hash(plain_password)
        item_data["Password"] = self._encode_aes(item_data["Password"])
        now_iso = self._now_iso()
        item_data["LastUsedAt"] = now_iso
        item_data["UpdatedAt"] = now_iso

        self.book_data["ItemList"].update({item_data["Index"]: item_data})
        self._register_item_password_hash(item_data["Index"], password_hash)
        self._sync_to_file()
        logger.info("已写入条目 %s", item_data["Index"])
        return item_data["Index"]

    def create_items_batch(self, items: list[KeyItem], user_password: str) -> list[str] | None:
        """
        批量新增条目（统一验证，统一落盘）
        :param items: 待新增条目列表
        :param user_password: 二级密码
        :return: 成功写入的条目ID列表；验证失败返回None
        """
        if not self._authorize_action(user_password, "批量导入条目"):
            return None

        created_ids: list[str] = []
        for data in items:
            try:
                item_data = data
                item_data["Index"] = self._get_index()
                item_data["PasswordLevel"] = self.get_password_level(item_data["Password"])
                plain_password = item_data["Password"]
                password_hash = self._password_plain_hash(plain_password)
                item_data["Password"] = self._encode_aes(item_data["Password"])
                now_iso = self._now_iso()
                item_data["LastUsedAt"] = now_iso
                item_data["UpdatedAt"] = now_iso

                self.book_data["ItemList"].update({item_data["Index"]: item_data})
                self._register_item_password_hash(item_data["Index"], password_hash)
                created_ids.append(item_data["Index"])
            except Exception as e:
                logger.warning("批量导入中跳过一条无效数据: %s", str(e))

        if created_ids:
            self._sync_to_file()
        return created_ids

    def remove_item(self, item_id: str, user_password: str) -> bool:
        """
        从文件中删除指定条目
        :param user_password: 二级密码
        :param item_id: 要删除的条目的Index
        :return: 是否删除成功
        """
        if not self._authorize_action(user_password, "删除条目"):
            return False

        if item_id in self.book_data["ItemList"]:
            self._unregister_item_password_hash(item_id)
            del self.book_data["ItemList"][item_id]
            self._sync_to_file()
            logger.info("已删除条目 %s", item_id)
            return True

        logger.warning("条目 %s 不存在，删除失败", item_id)
        return False

    def update_item(self, item_id: str, data: KeyItem, user_password: str):
        """
        修改条目
        :param user_password: 二级密码
        :param item_id: 要修改的条目编号
        :param data:新结构体
        :return:成功返回新条目索引，失败返回False
        """
        if not self._authorize_action(user_password, "修改条目"):
            return False

        if item_id in self.book_data["ItemList"]:
            stored_item = self.book_data["ItemList"][item_id]
            item_data = data
            old_password_hash = self._item_id_to_password_hash.get(item_id)
            if old_password_hash is None:
                old_password_hash = self._hash_password_from_encrypted_password(stored_item.get("Password", ""))

            item_data["Index"] = stored_item["Index"]
            item_data["LastUsedAt"] = stored_item.get("LastUsedAt", "")
            item_data["UpdatedAt"] = self._now_iso()
            if "Password" in item_data:
                new_password_hash = self._password_plain_hash(item_data["Password"])
                item_data["PasswordLevel"] = self.get_password_level(item_data["Password"])
                item_data["Password"] = self._encode_aes(item_data["Password"])
            else:
                new_password_hash = old_password_hash
                item_data["Password"] = stored_item["Password"]
                item_data["PasswordLevel"] = stored_item["PasswordLevel"]

            self.book_data["ItemList"].update({item_data["Index"]: item_data})
            if old_password_hash is not None:
                self._unregister_item_password_hash(item_id)
            if new_password_hash is not None:
                self._register_item_password_hash(item_id, new_password_hash)
            self._sync_to_file()
            logger.info("已更新条目 %s", item_data["Index"])
            return item_data["Index"]

        logger.warning("条目 %s 不存在，修改失败", item_id)
        return False

    def get_item(self, item_id: str, user_password: str) -> dict | None:
        """
        获取指定条目的（解密后）
        :param user_password: 用户密码，独立验证
        :param item_id: 指定条目索引
        :return: 解密后的单个条目
        """
        if not self._authorize_action(user_password, "查看条目"):
            return None

        if item_id in self.book_data["ItemList"]:
            target_item = self.book_data["ItemList"][item_id].copy()
            # 解密密码字段
            try:
                target_item["Password"] = self._decode_aes(target_item["Password"])
                self.book_data["ItemList"][item_id]["LastUsedAt"] = self._now_iso()
                self._deferred_sync_dirty = True
                return target_item
            except Exception as e:
                logger.warning("解密条目 %s 失败: %s", item_id, str(e))
                return None
        return None

    def flush_deferred_sync(self) -> bool:
        """将延迟写盘的改动统一落盘；若无改动则不执行写盘。"""
        if not self._deferred_sync_dirty:
            return False
        self._sync_to_file()
        return True

    def list_items(self) -> list:
        """
        获取所有条目（非密码字段）
        :return:
        """
        item_list = self.book_data.get("ItemList", {})
        non_secret_items = []

        allowed_fields = {
            "Index",
            "LinkURL",
            "Note",
            "PasswordLevel",
            "URL",
            "UserName",
            "LastUsedAt",
            "UpdatedAt",
        }

        for item_data in item_list.values():
            filtered_item = {
                field: item_data.get(field, "")
                for field in allowed_fields
                if field in item_data
            }
            if "LastUsedAt" not in filtered_item:
                filtered_item["LastUsedAt"] = ""
            if "UpdatedAt" not in filtered_item:
                filtered_item["UpdatedAt"] = ""
            non_secret_items.append(filtered_item)

        return non_secret_items

    def list_duplicate_password_items(self) -> list:
        """返回密码重复的条目（非敏感字段）。"""
        item_list = self.book_data.get("ItemList", {})
        if (not self._duplicate_index_ready) or self._duplicate_index_dirty:
            self._rebuild_duplicate_password_index()

        if len(self._item_id_to_password_hash) != len(item_list):
            self._rebuild_duplicate_password_index()

        duplicate_ids = {
            item_id
            for ids in self._password_hash_to_item_ids.values()
            if len(ids) > 1
            for item_id in ids
        }

        if not duplicate_ids:
            return []

        allowed_fields = {
            "Index",
            "LinkURL",
            "Note",
            "PasswordLevel",
            "URL",
            "UserName",
            "LastUsedAt",
            "UpdatedAt",
        }

        duplicate_items = []
        for item_id in duplicate_ids:
            item_data = item_list.get(item_id, {})
            filtered_item = {
                field: item_data.get(field, "")
                for field in allowed_fields
            }
            duplicate_items.append(filtered_item)

        return sorted(duplicate_items, key=lambda item: int(item.get("Index", "0")))

    def list_frequent_passwords(self, level: int | None = None):
        """
        获取常用密码
        :param level:常用密码的等级
        :return:
        """
        frequently_keys = self.book_data["FrequentlyKeys"]
        if level is None:
            return frequently_keys
        return {
            key: value
            for key, value in frequently_keys.items()
            if value.get("PasswordLevel") == level
        }

    def _verify_password(self, user_password: str) -> bool:
        """验证输入密码是否与当前主密码哈希匹配。"""
        try:
            self.verify_hasher.verify(self.verify_hash, user_password)
            return True
        except exceptions.VerifyMismatchError:
            return False

    def _authorize_action(self, user_password: str, action_name: str) -> bool:
        """统一处理敏感操作前的二级密码校验。"""
        is_verified = self._verify_password(user_password)
        if is_verified:
            logger.debug("主密码验证成功，允许%s", action_name)
        else:
            logger.warning("二级密码验证失败，拒绝%s", action_name)
        return is_verified

    # 私有（保护）函数
    def _init_or_load_file(self):
        """
        文件加载，验证，或初始化
        :return:
        """
        if not os.path.exists(self.path):
            self._initialize_new_book()
            return

        self.book_data = self._read_book_data()
        params = self._get_required_security_params()
        self._verify_login_password(params["verify_hash"])
        self._load_security_context(params)
        self._verify_file_integrity(params["integrity_check"])
        self._migrate_v2_session_kdf_to_strong_if_needed()
        self._migrate_kdf_if_needed()
        self._duplicate_index_ready = False
        self._duplicate_index_dirty = False

        logger.info("文件加载完成，验证通过")

    def _read_book_data(self) -> dict:
        """读取密码本文件内容。"""
        with open(self.path, 'r', encoding='utf-8') as book_file:
            try:
                return json.load(book_file)
            except json.JSONDecodeError:
                logger.warning("JSON文件格式错误，使用空文件重新初始化密码本")
                self._initialize_new_book()
                return self.book_data

    def _get_required_security_params(self) -> dict:
        """读取并验证安全配置字段是否完整。"""
        params = dict(self.book_data.get("ARGON2_PARAMS", {}))
        if "kdf_version" not in params:
            # 旧版本兼容：缺失时视为legacy版本
            params["kdf_version"] = self.KDF_VERSION_LEGACY

        required_params = [
            "kdf_version",
            "verify_hash",
            "hash_len",
            "encryption_salt",
            "hmac_salt",
            "hmac_key_encrypted",
            "integrity_check"
        ]
        missing = [param for param in required_params if param not in params]
        if missing:
            raise UnicodeError(f"文件参数不完整，缺少：{', '.join(missing)}")

        # 严格值校验
        validated = Argon2Params()
        try:
            validated.update(params)
        except Exception as e:
            raise UnicodeError(f"文件参数格式非法：{str(e)}")
        return validated

    def _verify_login_password(self, verify_hash: str):
        """校验登录密码并初始化 verify_hash。"""
        self.verify_hash = verify_hash
        try:
            self.verify_hasher.verify(self.verify_hash, self.main_key)
            logger.debug("主密码验证成功")
        except exceptions.VerifyMismatchError:
            raise InvalidPasswordError("输入的登录密码不正确")
        except exceptions.VerificationError:
            raise UnicodeError("哈希字符串格式错误")
        except Exception as e:
            raise RuntimeError(f"登录时发生未知错误 - {str(e)}")

    def _load_security_context(self, params: dict):
        """从配置中加载解密与完整性校验所需的安全材料。"""
        self.kdf_version = int(params["kdf_version"])
        self.encryption_salt = base64.b64decode(params["encryption_salt"])
        self.hmac_salt = base64.b64decode(params["hmac_salt"])
        self._aes_key_cache = None
        self._fernet_cache = None
        self.hmac_key = self._decrypt_hmac_key(params["hmac_key_encrypted"])

    def _migrate_kdf_if_needed(self):
        """将旧版本KDF数据迁移到当前版本，确保历史库可用。"""
        if self.kdf_version >= self.KDF_VERSION_CURRENT:
            return

        logger.info("检测到旧KDF版本：v%s，开始迁移到v%s", self.kdf_version, self.KDF_VERSION_CURRENT)

        item_password_plain: dict[str, str] = {}
        for item_id, item in self.book_data.get("ItemList", {}).items():
            encrypted_password = str(item.get("Password", ""))
            if not encrypted_password:
                continue
            item_password_plain[str(item_id)] = self._decode_aes(encrypted_password)

        frequent_password_plain: dict[str, str] = {}
        for key_id, fk_item in self.book_data.get("FrequentlyKeys", {}).items():
            encrypted_password = str(fk_item.get("Password", ""))
            if not encrypted_password:
                continue
            frequent_password_plain[str(key_id)] = self._decode_aes(encrypted_password)

        # 切换版本并失效缓存（后续派生使用新会话参数）
        self.kdf_version = self.KDF_VERSION_CURRENT
        self._aes_key_cache = None
        self._fernet_cache = None

        # 用新版本会话派生参数重加密业务数据
        for item_id, plain_password in item_password_plain.items():
            self.book_data["ItemList"][item_id]["Password"] = self._encode_aes(plain_password)

        for key_id, plain_password in frequent_password_plain.items():
            self.book_data["FrequentlyKeys"][key_id]["Password"] = self._encode_aes(plain_password)

        hmac_key_text = base64.b64encode(self.hmac_key).decode("utf-8")
        self.book_data["ARGON2_PARAMS"]["hmac_key_encrypted"] = self._encode_aes(hmac_key_text)
        self.book_data["ARGON2_PARAMS"]["kdf_version"] = self.kdf_version

        self._sync_to_file()
        logger.info("KDF版本迁移完成，已重写密码本文件")

    def _decrypt_hmac_key(self, encrypted_hmac_key: str) -> bytes:
        """解密并恢复持久化存储的 HMAC 密钥。"""
        try:
            hmac_key_text = self._decode_aes(encrypted_hmac_key)
            self._pending_v2_strong_migration = False
        except RuntimeError:
            if self.kdf_version != self.KDF_VERSION_CURRENT:
                raise
            logger.info("检测到v2旧会话派生参数数据，启用兼容读取")
            hmac_key_text = self._decode_aes(encrypted_hmac_key, hasher=self.legacy_session_hasher)
            self._pending_v2_strong_migration = True
        return base64.b64decode(hmac_key_text)

    def _migrate_v2_session_kdf_to_strong_if_needed(self):
        """将历史v2轻参数会话派生数据迁移为v2强参数。"""
        if not self._pending_v2_strong_migration:
            return

        logger.info("检测到v2旧会话派生参数，开始迁移到v2强参数")

        item_password_plain: dict[str, str] = {}
        for item_id, item in self.book_data.get("ItemList", {}).items():
            encrypted_password = str(item.get("Password", ""))
            if not encrypted_password:
                continue
            item_password_plain[str(item_id)] = self._decode_aes(
                encrypted_password,
                hasher=self.legacy_session_hasher,
            )

        frequent_password_plain: dict[str, str] = {}
        for key_id, fk_item in self.book_data.get("FrequentlyKeys", {}).items():
            encrypted_password = str(fk_item.get("Password", ""))
            if not encrypted_password:
                continue
            frequent_password_plain[str(key_id)] = self._decode_aes(
                encrypted_password,
                hasher=self.legacy_session_hasher,
            )

        # 失效缓存，后续使用v2强参数重加密
        self._aes_key_cache = None
        self._fernet_cache = None

        for item_id, plain_password in item_password_plain.items():
            self.book_data["ItemList"][item_id]["Password"] = self._encode_aes(plain_password)

        for key_id, plain_password in frequent_password_plain.items():
            self.book_data["FrequentlyKeys"][key_id]["Password"] = self._encode_aes(plain_password)

        hmac_key_text = base64.b64encode(self.hmac_key).decode("utf-8")
        self.book_data["ARGON2_PARAMS"]["hmac_key_encrypted"] = self._encode_aes(hmac_key_text)

        self._pending_v2_strong_migration = False
        self._sync_to_file()
        logger.info("v2会话派生参数迁移完成，已重写密码本文件")

    def _verify_file_integrity(self, expected_hmac: str):
        """校验密码本文件完整性。"""
        computed_hmac = self._compute_file_hmac(self.book_data)
        if not hmac.compare_digest(computed_hmac, expected_hmac):
            raise IntegrityError("文件HMAC校验失败，内容可能被篡改或损坏")

    def _initialize_new_book(self):
        """
        新建文件，初始化新密码
        用于文件不存在，或json文件格式错误时
        :return:
        """
        self.kdf_version = self.KDF_VERSION_CURRENT
        self.verify_hash = self.verify_hasher.hash(self.main_key)
        self.encryption_salt = secrets.token_bytes(16)
        self.hmac_salt = secrets.token_bytes(32)
        self._aes_key_cache = None
        self._fernet_cache = None
        self.hmac_key = self._derive_hmac_key()

        argon2_params = self._build_argon2_params()
        item_dict: dict[str, KeyItem] = {}
        frequently_key_dict: dict[str, FrequentlyKey] = {}

        self.book_data = {
            "ARGON2_PARAMS": argon2_params,
            "ItemList": item_dict,
            "FrequentlyKeys": frequently_key_dict
        }
        self._duplicate_index_ready = False
        self._duplicate_index_dirty = False
        self._sync_to_file()
        logger.info("新密码本初始化完成")

    def _password_plain_hash(self, plain_password: str) -> str:
        """计算明文密码哈希（仅用于内存索引，不落盘）。"""
        return hashlib.sha256(plain_password.encode("utf-8")).hexdigest()

    def _hash_password_from_encrypted_password(self, encrypted_password: str) -> str | None:
        if not encrypted_password:
            return None
        try:
            plain_password = self._decode_aes(str(encrypted_password))
        except Exception:
            return None
        return self._password_plain_hash(plain_password)

    def _register_item_password_hash(self, item_id: str, password_hash: str):
        if not item_id or not password_hash:
            return
        if not self._duplicate_index_ready:
            self._duplicate_index_dirty = True
            return
        self._item_id_to_password_hash[item_id] = password_hash
        id_set = self._password_hash_to_item_ids.setdefault(password_hash, set())
        id_set.add(item_id)

    def _unregister_item_password_hash(self, item_id: str):
        if not self._duplicate_index_ready:
            self._duplicate_index_dirty = True
            return
        password_hash = self._item_id_to_password_hash.pop(item_id, None)
        if not password_hash:
            return
        id_set = self._password_hash_to_item_ids.get(password_hash)
        if not id_set:
            return
        id_set.discard(item_id)
        if not id_set:
            self._password_hash_to_item_ids.pop(password_hash, None)

    def _rebuild_duplicate_password_index(self):
        """全量重建重复密码索引（初始化或异常兜底时使用）。"""
        self._password_hash_to_item_ids = {}
        self._item_id_to_password_hash = {}

        item_list = self.book_data.get("ItemList", {})
        for item_id, item in item_list.items():
            password_hash = self._hash_password_from_encrypted_password(item.get("Password", ""))
            if password_hash is None:
                continue
            item_id_str = str(item_id)
            self._item_id_to_password_hash[item_id_str] = password_hash
            id_set = self._password_hash_to_item_ids.setdefault(password_hash, set())
            id_set.add(item_id_str)
        self._duplicate_index_ready = True
        self._duplicate_index_dirty = False

    def _build_argon2_params(self) -> Argon2Params:
        """构建初始安全参数字典。"""
        encrypted_salt_b64 = base64.b64encode(self.encryption_salt).decode('utf-8')
        hmac_salt_b64 = base64.b64encode(self.hmac_salt).decode('utf-8')
        hmac_key_text = base64.b64encode(self.hmac_key).decode('utf-8')
        encrypted_hmac_key = self._encode_aes(hmac_key_text)

        argon2_params = Argon2Params()
        argon2_params["kdf_version"] = self.kdf_version
        argon2_params["verify_hash"] = self.verify_hash
        argon2_params["hash_len"] = 64
        argon2_params["encryption_salt"] = encrypted_salt_b64
        argon2_params["hmac_salt"] = hmac_salt_b64
        argon2_params["hmac_key_encrypted"] = encrypted_hmac_key
        argon2_params["integrity_check"] = "1234567890123456789012345678901234567890123456789012345678901234"
        return argon2_params

    def _compute_file_hmac(self, data: dict) -> str:
        """
        使用HMAC密钥计算文件HMAC
        :param data: 要计算的文件dict
        :return:hmac值
        """
        # 排除校验值本身（避免深拷贝带来的额外耗时）
        argon2_params = {
            key: value
            for key, value in data.get("ARGON2_PARAMS", {}).items()
            if key != "integrity_check"
        }
        data_to_check = {
            "ARGON2_PARAMS": argon2_params,
            "ItemList": data.get("ItemList", {}),
            "FrequentlyKeys": data.get("FrequentlyKeys", {}),
        }
        # 序列化HMAC计算器
        data_str = json.dumps(data_to_check,
                              sort_keys=True,
                              ensure_ascii=False,
                              indent=4,  # 增加缩进
                              separators=(',', ': ')
                              ).encode()

        # 计算HMAC（使用常驻内存的密钥）
        return hmac.new(
            self.hmac_key,
            msg=data_str,
            digestmod=hashlib.sha256
        ).hexdigest()

    def _sync_to_file(self):
        """将内存中的数据同步到文件，统一管理写入操作"""
        with open(self.path, 'w', encoding='utf-8') as file_handle:
            computed_hmac = self._compute_file_hmac(self.book_data)
            self.book_data["ARGON2_PARAMS"]["integrity_check"] = computed_hmac
            json.dump(self.book_data,
                      file_handle,
                      sort_keys=True,
                      ensure_ascii=False,
                      indent=4,
                      separators=(',', ': '))
        self._deferred_sync_dirty = False

    def _derive_hmac_key(self)->bytes:
        """使用hmac_salt派生HMAC密钥"""
        return self._derive_key(self.hmac_salt, 16, "HMAC密钥")

    def _encode_aes(self, plaintext: str, hasher: PasswordHasher | None = None) -> str:
        """
        使用AES加密明文
        :param plaintext: 要加密的明文（b64 str ）
        :return: 加密后的字符串（Base64编码，包含IV）
        """
        try:
            fernet = self._get_fernet(hasher=hasher)
            encrypted_token = fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted_token.decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"AES加密失败: {str(e)}")

    def _decode_aes(self, ciphertext: str, hasher: PasswordHasher | None = None) -> str:
        """
        使用cryptography的Fernet解密
        :param ciphertext: 加密后的令牌字符串
        :return: 解密后的明文
        """
        try:
            fernet = self._get_fernet(hasher=hasher)
            decrypted_bytes = fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            raise RuntimeError(f"AES解密失败（可能被篡改或密钥错误）: {str(e)}")

    def _get_fernet(self, hasher: PasswordHasher | None = None) -> Fernet:
        """
        生成Fernet加密器（封装了AES-GCM）
        """
        if hasher is None and self._fernet_cache is not None:
            return self._fernet_cache

        aes_key = self._derive_aes_key(hasher=hasher)
        fernet_key = base64.urlsafe_b64encode(aes_key)
        if len(fernet_key) != 44:
            raise ValueError(f"无效的Fernet密钥长度: {len(fernet_key)}")
        fernet = Fernet(fernet_key)
        if hasher is None:
            self._fernet_cache = fernet
        return fernet

    def _derive_aes_key(self, hasher: PasswordHasher | None = None) -> bytes:
        """
        使用加密专用盐值派生AES密钥,应该随用随调，使用后立刻清理
        """
        if hasher is None and self._aes_key_cache is not None:
            return self._aes_key_cache

        aes_key = self._derive_key(self.encryption_salt, 32, "AES密钥", hasher=hasher)
        if hasher is None:
            self._aes_key_cache = aes_key
        return aes_key

    def _derive_key(
        self,
        salt: bytes,
        key_length: int,
        key_name: str,
        hasher: PasswordHasher | None = None,
    ) -> bytes:
        """使用给定盐值派生指定长度的密钥。"""
        if not salt:
            raise RuntimeError(f"{key_name}盐值未初始化")
        try:
            active_hasher = hasher if hasher is not None else self._get_session_kdf_hasher()
            hash_result = active_hasher.hash(self.main_key, salt=salt)
            hash_bytes = self._extract_argon2_hash_bytes(hash_result)
            key_bytes = hash_bytes[:key_length]
            if len(key_bytes) < key_length:
                raise ValueError(f"哈希结果长度不足，无法生成{key_length}字节{key_name}")
            return key_bytes
        except Exception as e:
            raise RuntimeError(f"派生{key_name}失败: {str(e)}")

    def _get_session_kdf_hasher(self) -> PasswordHasher:
        """根据当前KDF版本选择会话派生参数。"""
        if self.kdf_version <= self.KDF_VERSION_LEGACY:
            return self.verify_hasher
        return self.session_hasher

    def _extract_argon2_hash_bytes(self, hash_result: str) -> bytes:
        """从 Argon2 结果字符串中提取原始哈希字节。"""
        parts = hash_result.split("$")
        if len(parts) < 6:
            raise ValueError(f"无效的Argon2哈希格式: {hash_result}")
        return self.argon2_base64_decode(parts[-1])

    def _get_index(self)->str:
        """
        获取一个新的条目index
        :return:
        """
        item_list = self.book_data.get("ItemList",{})
        if not item_list:
            return "1"
        max_index = max(int(key) for key in item_list)
        return str(max_index + 1)

    @staticmethod
    def _now_iso() -> str:
        """返回本地时间 ISO 字符串（精确到秒）。"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def get_password_level(key: str) -> int:
        """
        估计密码强度（0-5级，数字越大越安全）
        :param key: 待评估的密码字符串
        :return: 强度等级（0-5）
        """
        if not isinstance(key, str) or len(key) == 0:
            return 0
        score = 0  # 评分
        length = len(key)
        # 1. 密码长度评估（占比30%）
        if length >= 16:
            score += 3  # 超长密码（优秀）
        elif length >= 12:
            score += 2  # 长密码（良好）
        elif length >= 8:
            score += 1  # 标准长度（及格）
        # 小于8位不加分

        # 2. 字符类型多样性（占比40%）
        # 检查是否包含小写字母、大写字母、数字、特殊符号
        has_lower = re.search(r'[a-z]', key) is not None
        has_upper = re.search(r'[A-Z]', key) is not None
        has_digit = re.search(r'\d', key) is not None
        has_special = re.search(r'[^a-zA-Z0-9]', key) is not None

        # 每包含一种类型加1分，最多4分
        char_types = sum([has_lower, has_upper, has_digit, has_special])
        score += char_types

        # 3. 复杂度评估（占比30%）
        # 3.1 避免纯数字或纯字母
        if not (key.isdigit() or key.isalpha()):
            score += 1

        # 3.2 检查是否包含常见弱密码模式（如连续字符、重复字符）
        weak_patterns = [
            r'^[0-9]{6,}$',  # 纯数字且长度≥6
            r'^[a-zA-Z]{6,}$',  # 纯字母且长度≥6
            r'^(.)\1{4,}$',  # 单个字符重复≥5次（如aaaaa）
            r'^123456|654321|111111|abcdef|fedcba$'  # 常见序列
        ]
        is_weak_pattern = any(re.match(pattern, key.lower()) for pattern in weak_patterns)
        if not is_weak_pattern:
            score += 1

        # 3.3 检查是否包含常见词典词（简单检查）
        common_words = {'password', '123456', 'qwerty', 'admin', 'user', 'passwd', 'abc123'}
        if key.lower() not in common_words and not any(word in key.lower() for word in common_words):
            score += 1

        # 映射分数到0-5级（总分最高10分）
        level = min(5, max(0, (score // 2)))  # 10分→5级，8分→4级，以此类推
        return level

    @staticmethod
    def argon2_base64_decode(encoded: str) -> bytes:
        """
        手动解码Argon2使用的Base64变体（不依赖私有API）
        参考：https://github.com/P-H-C/phc-winner-argon2/blob/master/src/encoding.c
        """
        # 1. 替换特殊字符（Argon2用-代替+，用_代替/）
        encoded = encoded.replace('-', '+').replace('_', '/')

        # 2. 补充Base64填充符=（确保长度是4的倍数）
        padding_needed = (4 - (len(encoded) % 4)) % 4
        encoded += '=' * padding_needed

        # 3. 标准Base64解码
        return base64.b64decode(encoded)
