#!/bin/bash
# author: jay

function delete_mysql() {
    read -p "Please input mysql user: " mysqlUser
    read -p "Please input password: " -s mysqlPass

    echo "drop user sokoban@localhost;
    drop database sokoban
    drop database sokoban_middle_ware;
    exit;" | mysql -u$mysqlUser -p$mysqlPass
}

function delete_docker() {
    docker ps -a | while read containerId imageTag rest
    do
        [ "$imageTag" == "busyjay/sokoban:latest" ] && docker rm ${containerId}
    done
    docker rmi busyjay/sokoban:latest
}
read -p "Do you want to keep database data? (yes/no) " whetherKeepDb
[ "$whetherKeepDb" == "no" ] && delete_mysql
read -p "Do you want to keep docker image? (yes/no) " whetherKeepDocker
[ "$whetherKeepDocker" == "no" ] && delete_docker
rm -rf /usr/share/sokoban /var/log/sokoban /run/sokoban
userdel -rf sokoban


