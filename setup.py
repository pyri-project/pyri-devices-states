from setuptools import setup, find_packages, find_namespace_packages

setup(
    name='pyri-devices-states',
    version='0.1.0',
    description='PyRI Teach Pendant Devices States Service',
    author='John Wason',
    author_email='wason@wasontech.com',
    url='http://pyri.tech',
    package_dir={'': 'src'},
    packages=find_namespace_packages(where='src'),
    include_package_data=True,
    package_data = {
        'pyri.devices_states': ['*.robdef','*.yml']
    },
    zip_safe=False,
    install_requires=[
        'pyri-common',
        'pyri-device-manager',
        'robotraconteur',
        "asgiref"
    ],
    tests_require=['pytest','pytest-asyncio'],
    extras_require={
        'test': ['pytest','pytest-asyncio']
    },
    entry_points = {
        'pyri.plugins.robdef': ['pyri-sandbox-robdef=pyri.devices_states.robdef:get_robdef_factory'],
        'pyri.plugins.device_type_adapter': ['pyri-device-states-type-adapter = pyri.devices_states.device_type_adapter:get_device_type_adapter_factory'],
        'console_scripts': ['pyri-devices-states-service = pyri.devices_states.__main__:main']
    }
)