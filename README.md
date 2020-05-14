# ARCT
Android Remote Control Tool on Termux
## 这是什么？
这是一个 Android 远程管理工具，使用 Python、HTML 和 JavaScript 编写，依赖于 Termux:API 。主要使用的项目如下：
- Python
- Flask
- Bootstrap
- jQuery

本项目实用性并不是很强，主要是本人为了学习 Python Web 编程、jQuery 和 Bootstrap 的使用而编写的。

本项目具有以下特性：
- 完全使用AJAX动态加载，使用过程中不会发生页面跳转
- 部分的前后端分离
- 多用户管理
- 使用 Token 进行身份验证，登录具有时效性
- 密码本地储存为 Hash 值，增强安全性
- 多线程处理，实现在执行耗时较长的任务时，前台向后台主动请求获取执行状态（但并不能保证多个用户同时进行远程控制时无错误）

本项目的缺点：
- 对异常的捕获和处理不完全
- 代码结构不够清晰，后台与前台进行沟通时使用的方式不统一（json、数字、文本混用）
- 对用户非法操作的处理不佳，可能会造成程序运行异常
- 无法支持多用户同时操作，会造成后台处理混乱
## 预览
![](https://github.com/st1020/ARCT/raw/master/pic/1.jpg)
![](https://github.com/st1020/ARCT/raw/master/pic/2.jpg)
![](https://github.com/st1020/ARCT/raw/master/pic/3.jpg)
![](https://github.com/st1020/ARCT/raw/master/pic/4.jpg)
![](https://github.com/st1020/ARCT/raw/master/pic/4.jpg)
## 安装
```bash
pkg install python
pip install flask
git clone https://github.com/st1020/ARCT
```
## 运行
```bash
cd ARCT
python main.py
```
## 开源许可
本项目根据GNU General Public License, version 3 (GPL-3.0)开放源代码。
