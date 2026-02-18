FROM redis/redis-stack:latest

COPY ./cmake-build-default/xor_filter.so /tmp/xor_filter.so

CMD ["redis-stack-server", "--loadmodule", "/tmp/xor_filter.so"]