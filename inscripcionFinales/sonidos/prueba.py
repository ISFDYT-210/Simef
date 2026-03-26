import winsound
# winsound.Beep (440,1000)

#winsound.Beep (800, 500)


print ("indique la frecuencia del bepp que quiere reproducir: ")

a=int(input ())

if a>100:
    print ("reproduciendo beep a {a} " )
    winsound.Beep (a, 500)
else:
    print ("reproduciendo beep a {a} " )
    winsound.Beep (a, 1000)
