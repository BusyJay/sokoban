#!/bin/bash
# author: jay

function printHelp() {
    echo "Usage: $0 [options]"
    echo "  -h, print usage"
    echo "  -v, verbose outout"
}

function die() {
    echo "$1"
    exit
}

function setupMySQL() {
    mysql --version 2>&1 >/dev/null || die "It seems that you don't have mysql installed"

    read -p "Please input mysql user: " mysqlUser
    read -p "Please input password: " -s mysqlPass

    echo "create user sokoban@localhost identified by 'sokoban';
    create database sokoban;
    grant all privileges on sokoban.* to sokoban@localhost;
    create database sokoban_middle_ware;
    grant all privileges on sokoban_middle_ware.* to sokoban@localhost;
    " | mysql -u${mysqlUser} -p${mysqlPass}

    sokoban_manage.py syncdb
}

function configureUser() {
    git --version 2>&1 > /dev/null || die "Please install git and configure properly."

    # add sokoban user
    useradd -d /var/lib/sokoban -m -u 148 -r -c "Documentation synchonization tools" -s /sbin/nologin sokoban
    gpasswd -a sokoban docker

    # configure git
    su sokoban -s /bin/bash -c 'cd
    git config --global user.email "sokoban@localhost"
    git config --global user.name "sokoban"
    mkdir -m 700 /var/lib/sokoban/{middle_ware,working,tree,core}/
    '

    [ -d '/var/log/sokoban' ] || mkdir /var/log/sokoban
    [ -d '/run/sokoban' ] || mkdir /run/sokoban
    chown sokoban /var/log/sokoban /run/sokoban
}

function setupDocker() {
    docker ps 2>&1 > /dev/null || die "It seems that you don't have docker installed or docker daemon not started yet."

    dockerfile_root=/usr/share/sokoban/docker

    cd "$dockerfile_root/"
    docker build -t busyjay/sokoban .
}

verbose=">/dev/null"

while getopts "hv" opt
do
    case ${opt} in
        h)
            printHelp
            exit 0
            ;;
        v)
            verbose=""
            ;;
    esac
done


if [ "$( id -u )" != "0" ]; then
    echo "You are not runing this script as root, which may cause some privileges problems."
    read -p "Do you still want to continue? (yes/no) " whetherContinue
    if [ "$whetherContinue" == "no" ]; then
        exit
    fi
fi

echo "setting up docker..."
setupDocker ${verbose} || die "failed."
echo "setting up user sokoban..."
configureUser ${verbose} || die "failed."
echo "collecting static files..."
sokoban_manage.py collectstatic || die "failed."
echo "setting up database..."
setupMySQL ${verbose} || die "failed"
echo "done."