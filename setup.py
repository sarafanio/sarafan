from setuptools import setup, find_packages

setup(
    name='sarafan',
    version='0.1.0',
    url='https://github.com/sarafanio/sarafan.git',
    author='Sarafan Community',
    author_email='flu2020@pm.me',
    description='Sarafan node and client application. Sarafan is a distributed '
                'publication delivery network for anonymous.',
    packages=find_packages(),
    install_requires=[
        'core-service >= 0.1.0',
        'stem >= 1.8.0',
        'aiohttp >= 3.6.2',
        'aiohttp-cors >= 0.7.0',
        'aiohttp-socks >= 0.5.3',
        'eth_abi >= 2.1.0',
        'pycryptodomex >= 3.9.7',
        'eth_account >= 0.4.0',
        'yoyo_migrations >= 7.0.1',
        'async-timeout >= 3.0.1',
        'ConfigArgParse >= 1.2',
        'colorama >= 0.4.3',
        'dataclasses-json >= 0.5.2',
    ],
    entry_points={
        'console_scripts': [
            'sarafan = sarafan.cli:cli',
        ],
    },
    extras_require={
        'dev': [
            'pytest',
            'pytest-asyncio',
            'pytest-cov',
            'pylama',
            'mypy',
        ]
    }
)
