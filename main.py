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

"""程序入口与应用级初始化。"""
__version__ = "0.0.2.1"

import sys
import logging
import os
from PyQt5.QtWidgets import QApplication, QDialog

from UI import LoginDialog, MainWindow, ErrorDialog
from Core import PasswordNotebook, InvalidPasswordError, IntegrityError


def configure_logging():
    """配置默认日志级别，未显式指定时按发布模式仅输出警告及以上日志。"""
    level_name = os.getenv("KEYWORD_NOTEBOOK_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )


def main():
    """程序入口：初始化应用→登录→启动主界面"""
    configure_logging()
    app = QApplication(sys.argv)

    # 设置全局中性样式（具体控件风格由 UI 模块定义）
    app.setStyle("Fusion")
    app.setStyleSheet("""
                 QToolTip {
                     background: #0f172a;
                     color: #ffffff;
                     border: 1px solid #1e293b;
                     padding: 6px;
                     border-radius: 4px;
                 }
          """)

    # 2. 显示登录对话框
    login_dialog = LoginDialog()
    while True:
        if login_dialog.exec_() != QDialog.Accepted:  # 用户取消登录
            sys.exit(0)

        # 3. 初始化核心类（传入登录成功的主密码）
        try:
            password_book = PasswordNotebook(main_key=login_dialog.main_key)
            login_dialog.register_success()
            break
        except UnicodeError as e:
            error_msg = ErrorDialog(msg=f"文件损坏：{str(e)}",button="退出")
            error_msg.exec_()
            sys.exit(1)
        except InvalidPasswordError as e:
            # 密码错误：提示用户并重新显示登录界面
            login_dialog.register_failed_attempt()
            error_msg = ErrorDialog(msg=str(e),button="重新输入")
            error_msg.exec_()
        except IntegrityError as e:
            # 文件完整性异常：明确告知并终止
            error_msg = ErrorDialog(msg=f"文件安全异常：{str(e)}", button="退出")
            error_msg.exec_()
            sys.exit(1)
        except Exception as e:
            # 其他致命错误（如文件损坏、权限问题）：提示后退出
            error_msg = ErrorDialog(msg=f"初始化失败.系统错误：{str(e)}", button="退出")
            error_msg.exec_()
            sys.exit(1)

    # 4. 启动主界面
    main_window = MainWindow(password_book)
    main_window.show()  # 显示主窗口

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
