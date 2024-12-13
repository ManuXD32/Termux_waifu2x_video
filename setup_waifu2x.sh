#!/bin/bash

echo "Installing required packages..."
apt update && apt install vulkan-tools vulkan-headers clang build-essential make cmake python-pip python3 ffmpeg git -y

echo "Cloning waifu2x-ncnn-vulkan repository..."
git clone https://github.com/nihui/waifu2x-ncnn-vulkan.git
cd waifu2x-ncnn-vulkan || { echo "Failed to enter directory."; exit 1; }
git submodule update --init --recursive

echo "Cloning Google's Android NDK..."
git clone https://android.googlesource.com/platform/ndk.git ~/ndk

echo "Modifying libwebp CMakeLists.txt..."
sed -i '/if(ANDROID)/i set(ANDROID_NDK ~/ndk)' src/libwebp/CMakeLists.txt

echo "Modifying waifu2x CMakeLists.txt..."
sed -i 's|target_link_libraries(waifu2x-ncnn-vulkan ${WAIFU2X_LINK_LIBRARIES})|target_link_libraries(waifu2x-ncnn-vulkan PRIVATE ${WAIFU2X_LINK_LIBRARIES} android log)|' src/CMakeLists.txt

echo "Building waifu2x-ncnn-vulkan..."
mkdir -p ~/waifu2x-ncnn-vulkan/build
cd ~/waifu2x-ncnn-vulkan/build || { echo "Failed to enter build directory."; exit 1; }
cmake -DANDROID_ABI=arm64-v8a ../src
cmake --build . -j 4

echo "Removing old upscale2x binary..."
rm -f ~/../usr/bin/upscale2x

echo "Copying new binary to bin folder..."
cp ~/waifu2x-ncnn-vulkan/build/waifu2x-ncnn-vulkan ~/../usr/bin/upscale2x

echo "Copying models"
rm -rf ~/.upscaler_models/
mkdir ~/.upscaler_models
mv ~/waifu2x-ncnn-vulkan/models/* ~/.upscaler_models/

echo "Cleaning up"
rm -rf ~/ndk ~/waifu2x-ncnn-vulkan

echo "Setup complete!"
