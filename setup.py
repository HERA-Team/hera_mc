from distutils.core import setup

setup_args = dict(name=NAME,
                  maintainer=MAINTAINER,
                  maintainer_email=MAINTAINER_EMAIL,
                  description=DESCRIPTION,
                  long_description=LONG_DESCRIPTION,
                  url=URL,
                  download_url=DOWNLOAD_URL,
                  license=LICENSE,
                  classifiers=CLASSIFIERS,
                  author=AUTHOR,
                  author_email=AUTHOR_EMAIL,
                  platforms=PLATFORMS,
                  version=VERSION,
                  packages=PACKAGES,
                  package_data=PACKAGE_DATA,
                  scripts=SCRIPTS,
                  requires=REQUIRES)


if __name__ == '__main__':
    apply(setup, (), setup_args)
