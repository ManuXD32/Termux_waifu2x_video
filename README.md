## Termux_waifu2x_video
This repo tries to replicate the work of video2x, it uses tanyiok1234 waifu2x binaries.

## Installation:
  1.  Clone the repo and give execution permissions to the installer.sh script:
     ```
     chmod +x installer.sh
     ```
  2. Execute the installer:
     ```
     ./installer.sh
     If you want to compile waifu2x, execute chmod +x setup_waifu2x.sh && ./setup_waifu2x.sh instead of the installer
     ```
  3. Execute the help command of the python script:
     ```
     python video_upscaler.py --help
     ```

  The installer will clone tanyiok1234 repo with the termux binaries for using the waifu2x tool, it will also install ffmpeg, python3, the vulkan headers and git (just in case)
  Then it will move the models and put the binary into the usr/bin folder and rename it to upscaler2x.

  If you want to be able to also upscale videos using waifu2x, you can use the python script provided in this repo, it uses an implementation of chunks to be able to process large videos, as having a folder with 200000 frames will surely make it unusable.
  The syntax to use the script is this: 
  
      python video_upscaler.py input.mp4 output.mp4 scale_factor chunk_time model [cpu]

        The scale factor can be 2/4/8/16/32 if you compile the waifu2x binary, if you use the precompiled one you can only upscale by 2 or 4, if you choose 4, the frames will be upscaled twice (slower than upscaling by 2 with the binary compiled by yourself).
        For the chunk time I sugest using a maximum of 60 seconds, the script will use ffmpeg to split the original video in chunks of 60 seconds each.
        The model is optional, leaving it blanck will default to models-cunet, if you want to specify a different model you will need to write its name, the script will know where to look for it.
        Added an option to use cpu instead of gpu, the you just need to specify cpu at the end of the python call, if no cpu argument specified, the script will default to gpu. Using cpu is painfully slow, only advised if using gpu leads to glitches in the output or blank images.

      python video_upscaler.py resume
        As upscaling big videos can be so slow and the process may even stop, I have added this option.
        It will begin where the last job run on this folder left off, it works by keeping track of the last command job and the last processed chunk and frame.


## Build waifu2x binary on termux:
Follow the guide written in guide.txt or use the setup_waifu2x.sh script provided on this repo :)

By using the binary compiled by yourself, and if your GPU is compatible with vulkan, you can increase the speed of the upscaling and use the new python script to be able to upscale by higher factors way faster. 

If you couldn't use your GPU with the precompiled one or the frames came out as black, compiling it youself will probably solve the problem.

## How does it work?
  The python script will split the original video into several chunks depending on the time set by the user, it will then extract the frames of one chunk at a time, upscale it, rebuild an upscaled chunk, remove the chunk folder with the original frames and go to the next chunk until everything has been processed. Once it finishes, it will merge all of the chunks and add the original audio and subs track.


## WARNING!!
  This is a very intense process, your device might have visual glitches while upscaling because it's using all of its GPU resources. Trying to upscale very large videos will take several hours, even more if you are upscaling by 4 and the device can get very hot.

## CREDITS:
tanyiok1234 for the binaries https://github.com/tanyiok1234/waifu2x_srmd-ncnn-vulkan-termux-binary
k4yt3x because I took the idea from your awesome project https://github.com/k4yt3x/video2x
