from lib_vm import VM, RED
import logging, sys, json, os
from subprocess import call

log = logging.getLogger('manage-p2')

with open('manage-p2.json', 'r') as file:
    data = json.load(file)

numero = data["number_of_servers"]

def init_log():
    # Creacion y configuracion del logger
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger('auto_p2')
    ch = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
    ch.setFormatter(formatter)
    log.addHandler(ch)
    log.propagate = False

def create():
    call(["/lab/cnvr/bin/prepare-vnx-debian"])
    c1 = VM("c1") 
    c1.create_vm() 
    lb = VM("lb")
    lb.create_vm()

    if numero > 5 or numero < 1:
        log.error("Número de servidores inválido, introduzca un número de servidores de 1 a 5.")
        return
    log.debug("Número de vm válido")
    
    for n in range(1, numero + 1):
        nombre = f"s{n}"
        servidor = VM(nombre)
        servidor.create_vm()
    
    LAN1 = RED('LAN1')
    LAN1.create_red()
    LAN2 = RED('LAN2')
    LAN2.create_red()

    os.system("sudo ifconfig LAN1 up")
    os.system("sudo ifconfig LAN1 10.1.1.3/24")
    os.system("sudo ip route add 10.1.0.0/16 via 10.1.1.1")


    log.debug("Escenario creado correctamente")

def start(vm = None):
    if vm == None:
        #Iniciar  servidores
        for n in range(1, numero + 1):
            nombre = f"s{n}"
            s = VM(nombre)
            s.start_vm()
            s.show_console_vm()
            log.info(f"'{nombre}' iniciado correctamente.")
        
        # Iniciar  c1
        c1 = VM("c1")
        c1.start_vm()
        c1.show_console_vm()
        log.info("'c1' iniciado correctamente.")

        # Iniciar router lb
        lb = VM("lb")
        lb.start_vm()
        lb.show_console_vm()
        log.info("'lb' iniciado correctamente.")

        log.debug("Escenario arrancado correctamente")
        
    else:
        #Iniciamos una vm de manera individual
        vm = VM(vm)
        vm.start_vm()
        vm.show_console_vm()
        log.info(f"'{vm}' iniciado correctamente.")

def info(vm = None):
    if vm == None:
        for n in range(1, numero + 1):
            nombre = f"s{n}"
            servidor = VM(nombre)
            servidor.datos_vm()
            servidor.estado_vm()
            
    
        c1 = VM("c1")
        c1.datos_vm()
        c1.estado_vm()
        

        lb = VM("lb")
        lb.datos_vm()
        lb.estado_vm()
        
    else:
        vm = VM(vm)
        vm.datos_vm()
        vm.estado_vm()
        

def ping(vm):
    vm = VM(vm)
    vm.ping_vm()

def stop(vm = None):
    if vm == None:
        for n in range(1, numero + 1):
                nombre = f"s{n}"
                servidor = VM(nombre)
                servidor.stop_vm()
            
        c1 = VM("c1")
        c1.stop_vm()

        lb = VM("lb")
        lb.stop_vm()
    else:
        vm = VM(f"{vm}")
        vm.stop_vm()


def destroy():
    for n in range(1, numero + 1):
        nombre = f"s{n}"
        servidor = VM(nombre)
        if servidor.estado_vm() == "apagado":
            servidor.destroy_vm(apagado = True)
        else:
            servidor.destroy_vm()  
        
    c1 = VM("c1")
    if c1.estado_vm() == "apagado":
        c1.destroy_vm(apagado = True)
    else:
        c1.destroy_vm()  
        
    lb = VM("lb")
    if lb.estado_vm() == "apagado":
        lb.destroy_vm(apgado = False)
    else:
        lb.destroy_vm()  
    log.info("Router 'lb' destruido correctamente.")
        
    # Destruir redes LAN1 y LAN2
    LAN1 = RED("LAN1")
    LAN2 = RED("LAN2")
    LAN1.destroy_red()  
    LAN2.destroy_red()  
    log.info("Redes 'LAN1' y 'LAN2' eliminadas correctamente.")
    log.debug("Escenario destruido correctamente.")

#Main
init_log()
print('Practica Creativa 1 CDPS \n Realizada por: Gador Gómez, Marcos Chamorro y Álex Márquez')
print()

#sys.argv[n] Obtenemos el comando en la posicion n
command = sys.argv[1].lower()
if len(sys.argv) > 2:
    vm = sys.argv[2].lower()
else: 
    vm = None

if vm == None:
    if command == "create":
        create()
    elif command == "start":
        start()
    elif command == "info":
        info()
    elif command == "stop":
        stop()
    elif command == "destroy":
        destroy()
else:
    if command == "start":
        start(vm)
    elif command == "info":
        info(vm)
    elif command == "ping":
        ping(vm)
        print()
    elif command == "stop":
        stop(vm)
    else:
        log.error("Comando no válido, introduzca un comando válido.")
        sys.exit(1)  
