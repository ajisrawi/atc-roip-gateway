import sys

text = open(sys.argv[1], encoding='utf-8').read()
i = text.find('(net RMII_RXD0')
print(text[i:i + 200] if i >= 0 else 'NET NOT IN DSN')
