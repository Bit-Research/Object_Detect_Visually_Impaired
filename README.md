# object_detect_visually_impaired_one
Find the object and tell their name via audio for visually imparied one
$ git clone https://github.com/anandg-embedd/object_detect_visually_impared_one.git  #it is used to clone the code from the repository to your monitor

# Test the Camera
$libcamera-hello --list-cameras                                                      #for finding the pi camera is enabled or not in the raspberry pi

$vcgencmd get_camera                                                                 #if the command been fetched then, it must reply          supported=1 detected=1, libcamera interfaces=1; But normally for new edition raspberry pi 3b+ its already their as inbuilt to the hardware system

$ libcamera-still -o test.jpg                                                        #This command helps to execute the pi camera to take a snapshot and named as test.jpg

# Update OS
$ sudo apt update                                                                    #to update the OS for any installation

$ sudo apt upgrade -y                                                                #This is for upgrade the os after the installation

$ sudo apt full-upgrade -y                                                            #This is for upgrade the os after the installation

$ sudo apdate

# Camera Installation

$ sudo apt install -y python3-picamera2  

# Virtual env creation

$python3 -m venv myenv --system-site-packages                                        #To create a Virtual environment we use this cmd

$ source /home/pi/myenv/bin/activate 

# Run Code

$ cd object_detect_visually_impared_one/

$ cd main/

$ python3 main.py

# Instation for dependencies

$ pip install requests

$ pip install numpy

$ pip install pydub

$ pip install RPi.GPIO

# Verify GOIO

$ raspi-gpio set "GPIO pin no" dl

$ raspi-gpio set "GPIO pin no" dh

$ sudo lsof /dev/gpiomem

$ pinctr1 set "GPIO pin no" op

$ pinctrl set "GPIO pin no" dh
