# object_detect_visually_impaired_one
Find the object and tell their name via audio for visually imparied one
$ git clone https://github.com/anandg-embedd/object_detect_visually_impared_one.git  #it is used to clone the code from the repository to your monitor

$libcamera-hello --list-cameras                                                      #for finding the pi camera is enabled or not in the raspberry pi

$vcgencmd get_camera                                                                 #if the command been fetched then, it must reply          supported=1 detected=1, libcamera interfaces=1; But normally for new edition raspberry pi 3b+ its already their as inbuilt to the hardware system

$ libcamera-still -o test.jpg                                                        #This command helps to execute the pi camera to take a snapshot and named as test.jpg

$ sudo apt update                                                                    #to update the OS for any installation

$ sudo apt upgrade -y                                                                #This is for upgrade the os after the installation

$ sudo apt full-upgrade -y                                                            #This is for upgrade the os after the installation

$ nano camera_test.py                                                                 #To enter into the editor file camera_test.py page and                                                                                   can edit or fetch the code

$ sudo apt install picamera2  

$ python3 camera_test.py

$ python3 -m venv myenv                                                               #To create a Virtual environment we use this cmd


$ source /home/pi/myenv/bin/activate 


$ git pull origin main

$ cd object_detect_visually_impared_one/

$ cd main/

$ python3 main.py

$ nano main.py

$ python3 main.py

$ pip install requests

$ pip install numpy

$ pip install pydub

$ pip install RPi.GPIO

$ nano /home/pi/camera_test.py

$ python3 /home/pi/camera_test.py

$ python3 main.py

$ sudo raspi-config

$ raspi-gpio set "GPIO pin no" dl

$ raspi-gpio set "GPIO pin no" dh

$ raspi-gpio get

$ sudo lsof /dev/gpiomem

$ sudo reboot

$ pinctrl-h

$ pinctrl

$ pinctr1 set "GPIO pin no" op

$ pinctrl set "GPIO pin no" dh