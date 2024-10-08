for file in /usr/share/nginx/html/*; do
    if [ -f "$file" ]; then
        envsubst < "$file" > "$file.tmp" && mv "$file.tmp" "$file"
    fi
done

nginx -g daemon off;
