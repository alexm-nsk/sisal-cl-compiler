for OUTPUT in tests/*.json
do
	python main.py $OUTPUT
    echo "_________________________________"
done
