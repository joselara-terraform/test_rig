Library was created for Python 3.11. Reliability with other versions not tested.

Working on Windows 10-11, Ubuntu/Debian, MacOS Sonoma
For Spyder environment changes for fixing async functions can be necesary (not included). 


0) (not necessary) Install local python environment and activate it (python or python3).

python3 -m venv env

(Unix) . ./env/bin/Activate 
(Windows cmd) env\Scripts\activate.bat
(Windows powershell) env\Scripts\Activate.ps1

1) Instal requirements (pip or pip3):

pip3 install -r requirements

2) In cvm24p_example.py check connection settings. By default device address is 0xA1, baudrate 1000000. In case if you made changes, make corresponding changes in the file.

3) Run (python or python3)

python3 cvm24p_example.py


