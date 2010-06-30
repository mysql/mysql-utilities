import distutils.core, unittest, os

class TestCommand(distutils.core.Command):
    user_options = [ ]

    def initialize_options(self):
        self._dir = os.getcwd()
        # Install mock database
        # @todo add option to use real database later
        import sys, tests.MySQLdb
        sys.modules['MySQLdb'] = tests.MySQLdb

    def finalize_options(self):
        pass

    def run(self):
        "Finds all the tests modules in tests/, and runs them."

        import tests.command
        suite = unittest.TestSuite()
        suite.addTest(tests.command.suite())
        runner = unittest.TextTestRunner(verbosity=1)
        runner.run(suite)

distutils.core.setup(
    name='mysql-utilities', description='MySQL Command-line Utilities',
    maintainer="MySQL",         # !!!
    maintainer_email="internals@lists.mysql.com", # !!!
    version='0.1.0',
    url='http://launchpad.net/???', # !!! Launchpad URL
    packages=[ 'mysql' ],
    scripts=[
        'scripts/mysqlproc',
    ],
    classifiers=[
        'Programming Language :: Python',
    ],
    cmdclass = { 'test': TestCommand },
)
