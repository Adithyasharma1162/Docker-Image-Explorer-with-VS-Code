from flask import Flask, request
import docker
import tempfile
import tarfile
import io
import os

app = Flask(__name__)
client = docker.from_env()

def correct_image_name(image):
    """Correct common typos in image names."""
    corrections = {
        "ngnix": "nginx",
        # Add more common typos here if needed
    }
    repository, _, tag = image.partition(":")
    if not tag:
        tag = "latest"
    corrected_repository = corrections.get(repository, repository)
    return f"{corrected_repository}:{tag}"

def get_workdir_from_image(image):
    """
    Get the WORKDIR from the Docker image.
    If no WORKDIR is set, default to '/'.
    """
    try:
        image_attrs = client.images.get(image).attrs
        workdir = image_attrs['Config'].get('WorkingDir')
        return workdir if workdir else '/'
    except docker.errors.ImageNotFound:
        return '/'

def is_within_directory(directory, target):
    """Ensure target is within the given directory."""
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
    """
    Extract tar archive safely by stripping any leading '/'
    from both member names and, if applicable, their linknames.
    """
    for member in tar.getmembers():
        # Normalize and remove leading slashes from the file name.
        member.name = os.path.normpath(member.name.lstrip("/"))
        # If the member is a symlink or hard link, adjust its linkname too.
        if member.issym() or member.islnk():
            member.linkname = os.path.normpath(member.linkname.lstrip("/"))
        member_path = os.path.join(path, member.name)
        if not is_within_directory(path, member_path):
            raise Exception("Attempted Path Traversal in Tar File")
    tar.extractall(path, members, numeric_owner=numeric_owner)

@app.route('/')
def index():
    """Display a form to input the Docker image name."""
    return '''
    <h1>Open Docker Image Code in VS Code Server</h1>
    <form action="/start" method="post">
        <label for="image">Docker Image Name:</label><br>
        <input type="text" id="image" name="image" placeholder="e.g., nginx:latest" required><br><br>
        <input type="submit" value="Start VS Code Server">
    </form>
    '''

@app.route('/start', methods=['POST'])
def start():
    """Extract code from the image and launch VS Code Server with it."""
    image = request.form['image']
    image = correct_image_name(image)

    # Ensure the image is available locally; pull if necessary.
    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        try:
            client.images.pull(image)
        except docker.errors.ImageNotFound:
            return f"Error: Image '{image}' not found on Docker Hub."
        except docker.errors.APIError as e:
            if "pull access denied" in str(e):
                return f"Error: Pull access denied for '{image}'."
            else:
                return f"Error: {str(e)}"

    # Determine the WORKDIR from the image (defaulting to '/' if unset).
    workdir = get_workdir_from_image(image)

    # Create a temporary container from the image to access its filesystem.
    temp_container = client.containers.create(image, command='true')
    temp_container.start()

    try:
        # Get an archive (tar stream) of the contents at the WORKDIR.
        stream, stat = temp_container.get_archive(workdir)
        data = b"".join(stream)  # Concatenate all byte chunks.
        # Create a temporary host directory to store the code.
        host_code_dir = tempfile.mkdtemp(prefix="code_from_image_")
        # Extract the tar archive into host_code_dir using safe_extract.
        file_like = io.BytesIO(data)
        with tarfile.open(fileobj=file_like) as tar:
            safe_extract(tar, path=host_code_dir)
    except docker.errors.NotFound:
        return f"Error: Could not find the directory '{workdir}' in the image. Please verify the image contains your code."
    finally:
        temp_container.remove(force=True)

    # Remove any existing code-server container.
    code_server_container_name = 'codeserver'
    try:
        cs = client.containers.get(code_server_container_name)
        cs.stop()
        cs.remove()
    except docker.errors.NotFound:
        pass

    # Run the code-server container with the host folder (populated with the image’s code)
    # bind-mounted to /home/coder/project.
    client.containers.run(
        'codercom/code-server',
        command='--auth none',  # Disable authentication for simplicity
        detach=True,
        name=code_server_container_name,
        ports={'8080/tcp': 8080},
        volumes={host_code_dir: {'bind': '/home/coder/project', 'mode': 'rw'}}
    )

    return f'''
    <h1>Success!</h1>
    <p>VS Code Server is running at <a href="http://localhost:8080">http://localhost:8080</a>.</p>
    <p>The contents of the image's directory (WORKDIR: {workdir}) have been extracted to a temporary directory on the host and are mounted at <code>/home/coder/project</code> in VS Code Server.</p>
    <p>You should now see your project files in the VS Code file explorer.</p>
    '''

if __name__ == '__main__':
    app.run(port=5000, debug=True)
