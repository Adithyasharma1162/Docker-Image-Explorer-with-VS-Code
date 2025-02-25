# Docker-Image-Explorer-with-VS-Code
A tool that extracts the entire filesystem from a Docker image, mounts it into a VS Code Server container, and allows users to explore and edit the extracted files through a web-based VS Code instance.


# Features
✅ Extracts and mounts the complete filesystem of any Docker image
✅ Runs VS Code Server to enable web-based editing
✅ Supports common Linux-based Docker images
✅ Automatically handles container management and cleanup


# Usage

1. Run the Flask application using command

   ```
   python main.py
   ```

   Below will be displayed on `http://127.0.0.1:5000/`

  ![image](https://github.com/user-attachments/assets/953e22f7-1c44-4032-a2d2-f18410775de9)

2. Enter the docker image name and press 'Start VS Code Server'. Below will be displayed on the screen if the image exists

  Note that this may take some time to pull the image

  ![image](https://github.com/user-attachments/assets/8728e448-7004-4f0a-9e99-f1bd2a1757d9)


3. If you click on `http://localhost:8080/`, the window will be redirected to VS Code server as shown below
  The content of the image will be present in the **projects** directory

  ![image](https://github.com/user-attachments/assets/d9ec0ece-e37f-4cc1-ba2e-591aa09110c0)
