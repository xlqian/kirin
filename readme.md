Kirin
=====


                                                        /
                                                      .7
                                           \       , //
                                           |\.--._/|//
                                          /\ ) ) ).'/
                                         /(  \  // /
                                        /(   J`((_/ \
                                       / ) | _\     /
                                      /|)  \  eJ    L
                                     |  \ L \   L   L
                                    /  \  J  `. J   L
                                    |  )   L   \/   \
                                   /  \    J   (\   /
                 _....___         |  \      \   \```
          ,.._.-'        '''--...-||\     -. \   \
        .'.=.'                    `         `.\ [ Y
       /   /                                  \]  J
      Y / Y                                    Y   L
      | | |          \                         |   L
      | | |           Y                        A  J
      |   I           |                       /I\ /
      |    \          I             \        ( |]/|
      J     \         /._           /        -tI/ |
       L     )       /   /'-------'J           `'-:.
       J   .'      ,'  ,' ,     \   `'-.__          \
        \ T      ,'  ,'   )\    /|        ';'---7   /
         \|    ,'L  Y...-' / _.' /         \   /   /
          J   Y  |  J    .'-'   /         ,--.(   /
           L  |  J   L -'     .'         /  |    /\
           |  J.  L  J     .-;.-/       |    \ .' /
           J   L`-J   L____,.-'`        |  _.-'   |
            L  J   L  J                  ``  J    |
            J   L  |   L                     J    |
             L  J  L    \                    L    \
             |   L  ) _.'\                    ) _.'\
             L    \('`    \                  ('`    \
              ) _.'\`-....'                   `-....'
             ('`    \
              `-.___/


Setup
-----
 - Install dependencies with ``` pip install -r requirements.txt``` (virtualenv is strongly advised)
 - Create a configuration file by copying and editing ```kirin/default_settings.py```
 - You have to create a database as defined in the configuration file
 - You also need a redis-server, install it with ```sudo apt-get install redis-server```

```
sudo -i -u postgres
# Create a user
createuser -P navitia (password "navitia")

# Create database
createdb -O navitia kirin

# Create database for tests
createdb -O navitia chaos_testing
ctrl + d
```

 - Create a file ```.env``` with the path to you configuration file:
 ```
    KIRIN_CONFIG_FILE=default_settings.py
 ```
 - Build the protocol buffer files
```
git submodule init
git submodule update
./setup.py build_pbf
```
 - Build the version file: ```./setup.py build_version```
 - Setup the database (requires honcho):
```
pip install honcho
honcho run ./manage.py db upgrade
```
 - Run the developement server: ```honcho start```
 - Enjoy
