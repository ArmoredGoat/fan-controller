#!/usr/bin/env bash

### S E T   V A R I A B L E S

# Get directory name of install script no matter where it is beeing called from.
path_git_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Define necessary modules that are not already included in Python3.
python_modules=("numpy" "pigpio" "prometheus_client")

# Copy configuration file to ~/.config/fan-controller/
path_config_dir="$HOME/.config/fan-controller"
path_service_dir="$HOME/.config/systemd/user"

### F U N C T I O N S

create_directory () {
	# Funciton to check if directories exists. If not, create them.
	if [[ -d $@ ]]; then
        printf "Directory '$@': already existent.\n"
    else
        mkdir -p $@
        printf "Directory '$@': created.\n"
    fi
}

install_python3_module() {
    # Function to check if python modules are installed. If not, install them.
    
    # Update package lists.
    echo "Updating package lists..."
    sudo apt update

    for module in "$1"; do
        if ! python3 -c "import $module" &> /dev/null; then
            echo "Installing $module..."
            sudo apt install -y python3-$module
        fi
    done
}

### S E C T I O N   W H E R E   S T U F F   G E T S   D O N E

# Install necessary Python3 modules.
install_python3_module $modules

# Create directories for config and service files.
create_directory $path_config_dir $path_service_dir

# Copy config file in correct directory.
cp $path_git_dir/config/fan-controller.conf $path_config_dir

# Copy service file in service directory.
cp $path_git_dir/config/fan-controller.service $path_service_dir

# Set WorkingDirectory and ExecStart in service file to the correct path.
sed -i "s#^WorkingDirectory=#&$path_git_dir\/scripts#" \
    $path_service_dir/fan-controller.service

sed -i "s#^ExecStart=#&$path_git_dir\/scripts\/main.py#" \
    $path_service_dir/fan-controller.service

# Enable user-lingering. User lingering is a feature of systemd that keeps a 
# user session running after logouts, which allows users who are not logged 
# in to run long-running services.
# In this case, it allows to run the user service at boot without login in.
loginctl enable-linger 

# Enable service to start automatically on next boot.
systemctl --user enable fan-controller.service