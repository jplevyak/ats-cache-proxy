TSPREFIX=/opt/ts
TSXS=$(TSPREFIX)/bin/tsxs

%.so: %.c
	$(TSXS) -c $< -o $@

all: cacheurl.so

clean:
	rm -f *.lo *.so
