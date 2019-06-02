# This script is used to duplicate the server's data into the local
# version.
#
# As Fudul's data and its structures are getting larger, more complex
# and more interconnected, and since Django fails when it comes to
# conrner cases, it is important to use this bash script to go
# dump and load the data in a pre-determined order.
DUMP_DIR="dumps"
DUMP_DONE_DIR="dumps/done"
mkdir -p "$DUMP_DONE_DIR"

while read row; do
    DUMP_FILE=`echo $row | cut -d, -f1`
    DUMP_MODELS=`echo $row | cut -d, -f2`
    if [ ! -f "$DUMP_DIR/$DUMP_FILE" ] && [ ! -f "$DUMP_DONE_DIR/$DUMP_FILE" ]; then
      ssh fudul@fudul.webfactional.com "python3.6 manage.py dumpdata -v 3 --natural-foreign --natural-primary $DUMP_MODELS | xz" | unxz > "$DUMP_DIR/$DUMP_FILE"
    fi
    if [ -f "$DUMP_DONE_DIR/$DUMP_FILE" ]; then
      echo "Loading $DUMP_FILE was already done. Skipping."
    else
    	python manage.py loaddata -v 3 "$DUMP_DIR/$DUMP_FILE" || exit 1
    	echo "Loading $DUMP_FILE was successful"
    	mv "$DUMP_DIR/$DUMP_FILE" "$DUMP_DONE_DIR/$DUMP_FILE"
    fi
done < dump_order.csv
