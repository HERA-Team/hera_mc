Basic installation notes for testing on OS X


(HERA) djacobs@hayek:hera$ brew tap homebrew/services
==> Tapping Homebrew/services
Cloning into '/usr/local/Library/Taps/homebrew/homebrew-services'...
remote: Counting objects: 10, done.
remote: Compressing objects: 100% (7/7), done.
remote: Total 10 (delta 0), reused 6 (delta 0), pack-reused 0
Unpacking objects: 100% (10/10), done.
Checking connectivity... done.
Tapped 0 formulae (36 files, 164K)
(HERA) djacobs@hayek:hera$ brew services start postgresql
==> Successfully started `postgresql` (label: homebrew.mxcl.postgresql)
(HERA) djacobs@hayek:hera$ createuser  hera_test
(HERA) djacobs@hayek:hera$ createdb -Ohera_test -Eutf8 hera_mc
(HERA) djacobs@hayek:hera$ psql -U hera_test hera_mc
