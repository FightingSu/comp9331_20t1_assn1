#!/bin/bash

numberCnt=0
if [ $# == 2 ]
then
    numberCnt=$2
fi

randomPeer() {
    k=0
    shuf_str=`shuf -i 0-255 -n $numberCnt`
    shuf_str=$(printf "%s\n" "${shuf_str}" | sort -n)
    local peer_array=()
    for peer in ${shuf_str[@]}
    do
        peer_array[$k]=$peer
        let k++
    done

    peer_array[$k]=${peer_array[0]}
    peer_array[$((k + 1))]=${peer_array[1]}

    echo "${peer_array[*]}"
}

# remove all the txt files in under this path
find ./ -name "*.txt" -delete

# generate 12 random named files ranging from 0 to 9999 with random numbers
file_names=`shuf -i 0-9999 -n 12`
printf "\nfile names are:\n" 
for x in ${file_names[@]}
do 
    printf "$x "
    touch "$x.txt"
    echo `shuf -i 1-10000000 -n 3` >> $x.txt
done
printf "\n"



if [ $# == 2 ]
then
    printf '\nRandom peers are:\n'
    k=0
    for i in $(randomPeer) 
    do 
        printf "$i "
        peer_array[$k]=$i 
        let k++
    done 
    printf "\n\n"
else
    # an array showing a peer-to-peer network 2-4-5-7-2-4
    # peer_array=(2 4 5 7 2 4)
    # default 
    peer_array=(2 4 5 8 9 14 19 2 4)
fi

i=0
size=$((${#peer_array[@]} - 2))

# echo -e "The commands are:"
while [ $i -lt $size ]
do
#   printf "python3 p2p.py init ${peer_array[$i]} ${peer_array[$((i + 1))]} ${peer_array[$((i + 2))]} $1\n" 
    xterm -hold -title "Peer ${peer_array[$i]}" -e \
        "python3 p2p.py init ${peer_array[$i]} ${peer_array[$((i + 1))]} ${peer_array[$((i + 2))]} $1" &
    let i++
done
