from distutils.core import setup

setup(
    name='mysql-utilities', description='MySQL Command-line Utilities',
    maintainer="MySQL",         # !!!
    maintainer_email="internals@lists.mysql.com", # !!!
    version='0.1.0',
    url='http://launchpad.net/???', # !!! Launchpad URL
    packages=[ 'mysql' ],
    scripts=[
        'scripts/mysql-proc',
    ],
    classifiers=[
        'Programming Language :: Python',
    ],
)
