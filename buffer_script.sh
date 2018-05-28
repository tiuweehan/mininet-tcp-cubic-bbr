while true;
do
    tc -s -d qdisc show dev $2 | sed -n 's/.*backlog \([^ ]*\).*/\1/p';
    sleep $1;
done | ts -s '%H:%M:%.S;'
