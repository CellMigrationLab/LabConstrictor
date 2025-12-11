
proyectname = "adad"
version_number = "0.1.0"
proyectname_lower = proyectname.lower()

# PROYECT_NAME
conversion_dict = {
    "LOWER_PROJ_NAME": {
        "environment.yaml": proyectname_lower,
    },
    "PROJECT_NAME": {
        "construct.yaml": proyectname,
        "notebook_launcher.json": proyectname,
        "app/bash_bat_scripts/post_install.bat": proyectname,
        "app/bash_bat_scripts/post_install.sh": proyectname,
        "app/bash_bat_scripts/pre_uninstall.bat": proyectname,
        "app/bash_bat_scripts/pre_uninstall.sh": proyectname,
        "app/bash_bat_scripts/uninstall.sh": proyectname,
    },
    "VERSION_NUMBER": {
        "construct.yaml": version_number,
    },
    "WELCOME_IMAGE": {
        "construct.yaml": "app/logo/welcome.png",
    },
    "HEADER_IMAGE": {
        "construct.yaml": "app/logo/header.png",
    },
    "ICON_IMAGE": {
        "construct.yaml": "app/logo/logo.png",
    },
}