from setuptools import setup, find_packages

setup(
    name="firmware_file_server",
    version="0.1.0",
    description="A minimal Flask server to serve files (such as firmware) over HTTP and HTTPS.",
    author="Your Name",
    packages=find_packages(),
    py_modules=["firmware_file_server"],
    install_requires=[
        "Flask>=2.0.0",
    ],
    python_requires='>=3.7',
    entry_points={
        'console_scripts': [
            'firmware-file-server = firmware_file_server:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
