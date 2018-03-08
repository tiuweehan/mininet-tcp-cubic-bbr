while true;
do 
	STR=$(ss -tin);
	BBR=$(echo $STR | grep -oP "bbr:\([^\)]*");
	CWND=$(echo $STR | grep -oP "cwnd:[^\s]*");
	SSTHRES=$(echo $STR | grep -oP "ssthresh:[^\s]*");
	echo $BBR";"$CWND";"$SSTHRES";";
	sleep 0.04;
done | ts -s "%H:%M:%.S;";
