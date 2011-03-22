TSPREFIX=/opt/ts
CFLAGS=-g -I$(TSPREFIX)/include -fPIC

%.o: %.c
	$(CC) $(CFLAGS) -c $<

%.so: %.o
	$(CC) -shared $< -o $@

all: cacheurl.so

clean:
	rm -f *.o *.so
