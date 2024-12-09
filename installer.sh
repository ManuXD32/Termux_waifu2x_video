#!/bin/bash

apt update
apt upgrade -y
apt install python-pip python3 vulkan-headers git ffmpeg -y
git clone https://github.com/tanyiok1234/waifu2x_srmd-ncnn-vulkan-termux-binary.git
mv waifu2x_srmd-ncnn-vulkan-termux-binary/waifu2x-ncnn-vulkan/ ~/upscaler
mkdir ~/.upscaler_models
mv ~/upscaler/models-* ~/.upscaler_models
cp ~/upscaler/waifu2x-ncnn-vulkan ~/../usr/bin/upscaler2x
echo "Instalation finished, you can use the waifu2x upscaler by typing upscaler2x, to upscale videos you can use the provided python script in the github :)"
echo "The models are saved on ~/.upscaler_models, the default is models-cunet, but you will have to specify the path when using the tool -m ~/.upscaler_models/models-cunet"
