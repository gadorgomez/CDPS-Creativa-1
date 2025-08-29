import logging, os
from subprocess import call
from lxml import etree

log = logging.getLogger('manage-p2')

#Creamos el escenario 
servers = {"s1", "s2", "s3", "s4", "s5"}
bridges = {"c1":["LAN1"],
        "lb":["LAN1"],
        "s1":["LAN2"],
        "s2":["LAN2"],
        "s3":["LAN2"],
        "s4":["LAN2"],
        "s5":["LAN2"]}
network = {
        "c1":["10.1.1.2", "10.1.1.1"],
        "s1":["10.1.2.11", "10.1.2.1"],
        "s2":["10.1.2.12", "10.1.2.1"], 
        "s3":["10.1.2.13", "10.1.2.1"],
        "s4":["10.1.2.14", "10.1.2.1"],
        "s5":["10.1.2.15", "10.1.2.1"]}

netmask = "255.255.255.0"


def edit_xml (vm):
    #Obtenemos el directorio de trabajo actual
    cwd = os.getcwd()  
    path = cwd + "/" + vm

    #Creamos un arbol estructurado con el XML de la máquina pasada como parámetro
    tree = etree.parse(path + ".xml")
    #Se obtiene la raíz del árbol con la que podemos acceder a los elementos fijos
    root = tree.getroot()

    #Se define el nombre de la máquina, cambiando el valor de la etiqueta <name> por el nombre de la máquina pasada como parámetro
    name = root.find("name")
    if name is not None:
        name.text = vm

    #Se define el path de la máquina, cambiando el valor de la etiqueta <source file> por el path de la máquina pasada como parámetro
    source = root.find("./devices/disk/source")
    if source is not None:
        source.set("file", path + ".qcow2")

    #Se define el bridge de la máquina, cambiando el valor de la etiqueta <source bridge> por el bridge de la máquina pasada como parámetro
    bridge = root.find("./devices/interface/source")
    if bridge is not None:
        bridge.set("bridge", bridges[vm][0])

    #Con esto abrimos archivo "xml" en modo escritura, y escribimos en él el XML modificado (si no existe se crea)
    with open(path + ".xml" ,"w") as xml :
        #Escribimos el XML modificado en el archivo "xml"
        xml.write(etree.tounicode(root, pretty_print=True))  

    #Mofidicamos xml de todos los servidores para que tengan un virtualport tipo openvswitch
    #Tenemos xml_bueno que esta en modo lectura y xml_temporal que esta en modo escritura y es el que se va a modificar.
    #Se recorre el xml_bueno y se va escribiendo en el xml_temporal, y si se encuentra la etiqueta <interface type="bridge"> se añade la etiqueta <virtualport type="openvswitch">
    xml_original = open(path + ".xml",'r')
    xml_temporal = open("temporal.xml",'w')
    for linea in xml_original:
        xml_temporal.write(linea)
        if '<interface type="bridge">' in linea:
            xml_temporal.write("\n<virtualport type='openvswitch'/>\n")
    xml_original.close()
    xml_temporal.close()
    #Sustituimos el XML original por el temporal, y eliminamos el temporal
    call(["cp","./temporal.xml", path + ".xml"])  
    call(["rm", "-f", "./temporal.xml"])
    
    #Lo hacemos solo para lb, ya que es el único que tiene dos LAN y hay que añadirle un campo interface nuevo
    if vm == "lb" :
        xml_original = open(path + ".xml",'r')   #XML correspondiente a lb, en modo solo lectura
        xml_temporal = open("temporal.xml",'w')  #XML temporal abierto en modo escritura
        for linea in xml_original:
            xml_temporal.write(linea)
            if "</interface>" in linea:
                xml_temporal.write("\n<interface type='bridge'>\n <source bridge='"+"LAN2"+"'/>\n <model type='virtio'/>\n <virtualport type='openvswitch'/>\n </interface>\n")
        xml_original.close()
        xml_temporal.close()
        call(["cp","./temporal.xml", path + ".xml"])  
        call(["rm", "-f", "./temporal.xml"])

def config_network(vm):
    
    with open("hostname", "w") as hostname: 
        hostname.write(vm + "\n")  
    #Copiamos el archivo hostname a la MV correspondiente y lo colocamos en /etc
    call(["sudo", "virt-copy-in", "-a", vm + ".qcow2", "hostname", "/etc"])
    call(["rm", "-f", "hostname"])
    #Editamos el archivo /etc/hosts de la MV correspondiente para añadir la dirección IP de la MV
    call(["sudo", "virt-edit", "-a", f"{vm}.qcow2", "/etc/hosts","-e", f"s/127.0.1.1.*/127.0.1.1 {vm}/"])
    
    with open("interfaces", "w") as interfaces:
        #En lb se añaden las configuraciones de eth1 y eth0
        if vm == "lb":
            interfaces.write("auto lo\niface lo inet loopback\n\nauto eth0\niface eth0 inet static\n    address 10.1.1.1\n    netmask " + netmask + "\nauto eth1\niface eth1 inet static\n    address 10.1.2.1\n    netmask " + netmask)
        #En las demás máquinas se añade la confiuracion eth0 con la dirección IP correspondiente y la dirección del LB en gateway
        else:
            interfaces.write("auto lo \niface lo inet loopback \n\nauto eth0 \niface eth0 inet static \n    address " + network[vm][0] + " \n    netmask " + netmask + "\n    gateway " + network[vm][1])
            
    #Copiamos el archivo interfaces a la MV correspondiente y lo colocamos en /etc/network
    call(["sudo", "virt-copy-in", "-a", vm + ".qcow2", "interfaces", "/etc/network"])
    call(["rm", "-f", "interfaces"])
    #Habilitamos forwarding IPv4 para que lb funcione como router al arrancar
    if vm == "lb":
        call("sudo virt-edit -a lb.qcow2 /etc/sysctl.conf -e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/'", shell=True)

class VM:
    def __init__(self, name):
        self.name = name
        
    def create_vm(self):
        log.debug(f'Creando VM {self.name}')
        
        #Se crean las vm a partir de la imagen base
        call(["qemu-img","create", "-F", "qcow2", "-f", "qcow2", "-b", "./cdps-vm-base-pc1.qcow2",  self.name + ".qcow2"])
        log.debug(f"Imagen {self.name}.qcow2 creada con éxito.")
        
        #Se modifican archivos de configuración de las vm (los xmls)
        call(["cp", "plantilla-vm-pc1.xml", self.name + ".xml"])
        edit_xml(self.name)
        log.debug(f"Fichero {self.name}.xml modificado con éxito.")
        
        #Definimos las maquinas virtuales
        call(["sudo", "virsh", "define", self.name + ".xml"])
        log.debug(f"Definida MV {self.name}")
        
        #Configuramos las redes de las maquinas virtuales
        config_network(self.name)
        log.info(f"Se ha configurado la red de MV {self.name}")
        
    def start_vm(self):
        log.debug(f'Arrancando VM {self.name}')
        #Arrancamos las maquinas virtuales 
        call(["sudo", "virsh", "start", self.name])
        log.info(f"Se ha arrancado VM {self.name}")

        
    def show_console_vm(self):
        log.debug(f'Mostrando consola de maquina virtual {self.name}')
        #Abrimos terminal nuevo para cada vm
        os.system("xterm -rv -sb -rightbar -fa monospace -fs 10 -title '" + self.name + "' -e 'sudo virsh console "+ self.name + "' &")
    
    def datos_vm(self):
        log.debug(f'Mostrando datos de maquina virtual {self.name}')
        #Mostramos los datos de la vm
        call(["sudo", "virsh", "dominfo", self.name])
        log.info(f"Datos de VM {self.name} mostrados correctamente.")
    
    def estado_vm(self):
        log.debug(f'Mostrando estado de maquina virtual {self.name}')
        #Mostramos el estado de la vm
        result = call(["sudo", "virsh", "domstate", self.name])
        self.is_running = (result == 0)
        log.info(f"Estado de VM {self.name} mostrado correctamente. Ejecutándose: {self.is_running}")
        
    def ping_vm(self):
        log.debug(f'Haciendo ping a la maquina virtual {self.name}')
        #Hacemos ping a la vm
        if self.name == "lb":
            os.system("ping -c 4 10.1.1.1")
        else:
            os.system(f"ping -c 4 {network[self.name][0]}")
    
    def stop_vm(self):
        log.debug(f'Apagando VM {self.name}')
        #Apagamos las maquinas virtuales
        call(["sudo", "virsh", "shutdown", self.name])
        log.info(f"Se ha detenido VM {self.name}")

    
    def destroy_vm(self, apagado=False):
        log.debug(f'Destruyendo VM {self.name}')
        if apagado== False:
            call(["sudo", "virsh", "destroy", self.name])
        #Desdefinimos las maquinas virtuales
        call(["sudo", "virsh", "undefine", self.name])
        apagado= False
        #Eliminamos los archivos de configuración de las vm
        os.remove(f"{self.name}.qcow2")
        os.remove(f"{self.name}.xml")
        log.info(f"Se ha destruido VM {self.name}")


class RED:
    def __init__(self, name):
        self.name = name
        log.debug(f'Inicializando Network {name}')
        
    def create_red(self):
        log.debug(f'Creando la red {self.name}')
        call(["sudo", "ovs-vsctl", "add-br", self.name])
        log.debug(f"Bridge {self.name} creado con éxito.")
    
    def destroy_red(self):
        log.debug(f'Destruyendo la red {self.name}')
        call(["sudo", "ovs-vsctl", "del-br", self.name])
        log.debug(f"Bridge {self.name} eliminado con éxito.")