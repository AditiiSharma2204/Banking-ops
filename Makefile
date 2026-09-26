CC      ?= gcc
CFLAGS  ?= -std=c99 -Wall -Wextra -Wpedantic -O2
LDLIBS  = -lm
TARGET  = banking_ops

all: $(TARGET)

$(TARGET): banking_ops.c
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

run: $(TARGET)
	./$(TARGET)

test: $(TARGET)
	sh tests/smoke_test.sh ./$(TARGET)

clean:
	rm -f $(TARGET) $(TARGET).exe

.PHONY: all run test clean
