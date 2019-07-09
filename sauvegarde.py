# coding: utf-8

import os
from os import stat
from stat import *
import pwd
import grp
import pathlib
import time
import sys
import hashlib
import distutils.core
#import apt
import ftplib
import fileinput

def initialization():
    """ Method checking if config-file exists in /etc/apt/WP-save/settings.conf exists. If not, it creates it. """

    test = os.path.exists('/etc/apt/WP-save/settings.conf')

    if test == False:
        path = os.path.exists('/etc/apt/WP-save')
        if path == False:
            os.makedirs('/etc/apt/WP-save', exist_ok=True)
        settings = open('/etc/apt/WP-save/settings.conf', "w+")
        contains = """
# Do not use space after the "="
[Directories]
Dir_to_save=/etc/apt/.docker/apache2/www/html/wordpress/
Dir_of_saved=/etc/apt/.docker/savepath/
[mysql]
host=
user=
password=
[FTP]
FTP_host=
FTP_user=
FTP_password=
FTP_port=21
        """
        settings.write(contains)
        os.chown('/etc/apt/WP-save/settings.conf',0 ,0)
        os.chmod('/etc/apt/WP-save/settings.conf', 0o660)
        settings.close()

        logging("Settings didn't exists. It has been created. Please modify /etc/apt/WP-save/settings.conf with the appropriates settings then rerun this script")
        sys.exit()

class existence_checker():
    """ This object check if a file exists. It returns a boolean state "True" or "False"
    The result is stored under the "state" attribute
    The path is stored under the "name" attribute """

    def __init__(self, address):
        self.name = address
        self.state = self.test_existence(address)

    def test_existence(self, address):
        """ This method will try to open the given path, if success returns "True", else returns "False" """
        test = os.path.exists(address)
        return test

class log():
    """ This object create an entry with the following format:
    %d %B %H:%M:%S>>  (Message) """

    def __init__(self, message):
        instant = time.strftime("%d %B %H:%M:%S")
        self.entry = instant + " >> " + message

class files():
    """ This class creates an instance containing a dictionnary.
    The dictionnary will contain for each key the name of a file / folder with its type (f or d), owner (id:grp) permission and checksum.
    For optimisation checksum are not calculated here """

    def __init__(self, address):
        self.dict = {}
        self.list = []
        self.fileamount = 0
        self.folderamount = 0
        self.prefix = address
        self.hasher = hashlib.md5()
        self.make_list(address)
        self.hashed = self.hasher.hexdigest()


    # First we make a list of all objects in the given path (returns files and folders)
    def make_list(self, path, folder=''):
        list = os.listdir(path)
        for o in list:
            o = folder + o
            self.list.append(o)
            self.test_files(self.list, self.prefix)

    # Second we test all elements to know if it is a file
    def test_files(self, testlist, prefix):
        tmp = []
        for f in testlist:
            # The make_list only give name, but to be tested we have to provide the absolute path, we add it here
            file = f
            f = prefix + f
            isfile = os.path.isfile(f)
            # Test if it is a file or not
            if isfile == True:
                own = owner(f)
                perm = permission(f)
                check = self.checksum(f)
                # If so, we add it to the main dictionnary
                self.dict[f] = {'type' : 'f', 'owner' : own, 'permissions' : perm, 'checksum' : check }
                self.fileamount += 1
                # Avoiding infinite loop, we delete the name of the object from the list of objects to test
                self.list.remove(file)
            else:
                # Avoiding infinite loop, we delete the name of the object from the list of objects to test
                self.list.remove(file)
                # If not we store it in a temporary list
                tmp.append(f)
        # We add the / at the end of the suspected folder name, in order to maintain a good syntax for absolute path
        file = file + '/'
        # We send all the object wich aren't files to be tested as a folder
        self.test_directory(tmp,file)

    # Finaly we test if the objects are folder
    def test_directory(self, testpath, prefix):
        for d in testpath:
            isfolder = os.path.isdir(d)
            # If it is a folder we add it as a folder to the main dictionnary
            if isfolder == True:
                own = owner(d)
                perm = permission(d)
                self.dict[d] = {'name' : d, 'type' : 'd', 'owner' : own, 'permissions' : perm, 'checksum' : '' }
                self.folderamount += 1
                # We know we have a folder, we make the list of all objects it can contain (and restart an other loop)
                new_list = self.make_list(d,prefix)
            else:
                # If it's not a folder, it's not a file neither, logging an error
                logging('ERROR: ' + d + ' is nor a file nor a folder. Ignoring this object\n')

    def checksum(self, file):
        """Calculate checksum of a file"""
        with open(str(file), 'rb') as afile:
            buf = afile.read()
            file_hash = hashlib.md5(buf)
            self.hasher.update(buf)
        return file_hash.hexdigest()

def logging(text):
    """ This method write down the given text on screen and in a log """
    filelog = open("save.log", "a+")
    message = log(text)
    print (text)
    filelog.write(message.entry)
    filelog.close()

def owner(path):
    """ This method returns the owner (uid:gid) of the given object (absolute path)"""
    st = os.stat(path)
    uid = st.st_uid
    gid = st.st_gid
    name = pwd.getpwuid(uid).pw_name
    group = grp.getgrgid(gid).gr_name
    owner = str(uid) + ':' + str(gid)
    return owner

def permission(path):
    """ This method returns the permissions in octal mode of the given object (absolute path)"""
    permissions = oct(os.stat(path)[ST_MODE])[-3:]
    return permissions

def correct_owner_perm(origin, dest):
    """ This method correct compare owner of the filename given in dest with the same filename in origin dict. It correct it when needed """
    tmp_origin = {}
    tmp_dest = {}
    for name in origin:
        tronkated = name.split('/')
        tronkated = tronkated[-1]
        tmp_origin[tronkated] = origin[name]
    for name in dest:
        tronkated = name.split('/')
        tronkated = tronkated[-1]
        tmp_dest[tronkated] = dest[name]
    for file, data in tmp_dest.items():
        compare = tmp_origin[file]
        if data['owner'] != compare['owner']:
            owner = compare['owner'].split(':')
            user = int(owner[0])
            group = int(owner[1])
            target = save_dir + day + '/' + file
            os.chown(target, user, group)
            data['owner'] = compare['owner']
            logging('Mismatch detected on ' + file + "'s ownership. Corrected\n")
    for file, data in tmp_dest.items():
        compare = tmp_origin[file]
        if data['permissions'] != compare['permissions']:
            perm = compare['permissions']
            target = save_dir + day + '/' + file
            os.chmod(target, perm)
            data['permissions'] = compare['permissions']
            logging('Mismatch detected on ' + file + "'s permissions. Corrected\n")

def searchline(search):
    """ This method search a specific enter in the settings.conf file and returns the entry """

    searchfile = open("/etc/apt/WP-save/settings.conf", "r")
    for line in searchfile:
        if search in line:
            line = line.split('=')
            string = line[1]
            string = string[:-1]
            return string
    searchfile.close()

#def checkinstalled(apt):
    # """ This method checks if an apt is installed, and install it if not """
    # cache = apt.Cache()
    # cache.update()
    # cache.open()
    # logging('Check if ' + apt + 'is installed\n')
    # if cache[apt].is_installed:
    #     logging('Succeed: ' + apt + 'is installed\n')
    # else:
    #     logging('Failed. ' + apt + "isn't installed. Installing it\n")
    #     cache[apt].mark_install()
    #     try:
    #         cache.commit()
    #     except Exception :
    #         print(sys.stderr, "FATAL ERROR: Package install for {} as failed \n".format(apt))

def transfert(**kwargs):
    """ This method transfer the given file to given FTP server using credentials provided """
    ftp = ftplib.FTP()
    ftp.connect(kwargs['ftp'],int(kwargs['port']))
    ftp.login(kwargs['user'],kwargs['pass'])
    fp = open(kwargs['file'], 'rb')
    name = kwargs['file'].split('/')
    name = name[-1]
    filelist = ftp.nlst()
    if len(filelist) < 1:
        ftp.mkd(day)
    exists = False
    for f in filelist:
        if f.split()[-1] == day:
            logging("Cleanning old " + day + " backup")
            cleanOutFTP(ftp, day)
            ftp.mkd(day)
            exists = True
            break
    if exists == False:
        ftp.mkd(day)
    root = ftp.pwd()
    ftp.cwd(root + '/' + day)
    ftp.storbinary('STOR ' + name, fp, 1024)
    fp.close()
    ftp.quit()

def FTP_check_integrity(**kwargs):
    """ This method download a file """
    name = kwargs['file']
    test = open(name, 'wb')
    ftp = ftplib.FTP()
    ftp.connect(kwargs['ftp'],int(kwargs['port']))
    ftp.login(kwargs['user'],kwargs['pass'])
    ftp.cwd(day)
    ftp.retrbinary('RETR ' + name, test.write)
    test.close()
    hash = checksum('WP-BACKUP.tar.gz')
    ftp.quit()
    os.remove(kwargs['file'])
    return hash

def cleanOutFTP(ftp, target):
    """ Clean out a directory """
    if type(target) is not list:
        target = target.split()

    for d in target:
        try:
            ftp.delete(d)
        except:
            ftp.cwd(d)
            cleanOutFTP(ftp, ftp.nlst())
            ftp.cwd('..')
            ftp.rmd(d)

def compress(file):
    """ This method compress a folder into with tar """
    import tarfile
    with tarfile.open(save_path + 'WP-BACKUP.tar.gz', "w:gz") as tar:
        tar.add(file)

def checksum(file):
    """ Calculate checksum of a file """
    with open(str(file), 'rb') as afile:
        hasher = hashlib.md5()
        buf = afile.read()
        file_hash = hashlib.md5(buf)
        hasher.update(buf)
    return hasher.hexdigest()

## Pre-Steps

initialization()
save_dir = searchline('Dir_of_saved')
target_dir = searchline('Dir_to_save')
logging("STARTING SAVE PROCESS OF WORDPRESS FOLDER & WORDPRESS DATABASES \n")


## Step 1: Check the existences of the directory to save.
wp_path = existence_checker(target_dir)
if wp_path.state == False:
    logging("Fatal error: Wordpress's directory not found. Exit.\n")
    sys.exit()


## Step 2: Check of the existences of the save dir.
save_path = existence_checker(save_dir)
if save_path.state == False:
    logging("Save path does not exists. Creating it \n")
    os.system("sudo mkdir -p " + save_dir)


## Step 3: Check if the daily folder is ready
day = time.strftime("%A")
save_path = save_dir + day + '/'
test_path = existence_checker(save_path)
if test_path.state == False:
    logging("Daily Folder does not exist. Creating it. \n")
    os.system("sudo mkdir -p " + save_path)
else:
    os.system("sudo rm -r " + save_path)
    os.system("sudo mkdir -p " + save_path)
    logging(day + " folder cleared \n")



## Step 4: Copying target_dir in save_path
# Step 4.1: Create a list of files and folder and check owner and permission
logging ("Starting original files scan\n")
list_to_save = files(target_dir)
logging ('There are ' + str(list_to_save.fileamount) + ' files to save\n')
logging ('There are ' + str(list_to_save.folderamount) + ' folders to save \n')

# Step 4.2: Copy the target directory to the save directory
logging ("Copying...\n")
distutils.dir_util.copy_tree(target_dir,save_path)

# Step 4.2 Check & correct owner and permissions
logging ("Starting copied files scan\n")
list_of_saved = files(save_path)
logging ('There are ' + str(list_of_saved.fileamount) + ' files saved\n')
logging ('There are ' + str(list_of_saved.folderamount) + ' folders saved \n')
correct_owner_perm(list_to_save.dict, list_of_saved.dict)

# Step 4.3 Checksum (stop if failed)
if list_to_save.hashed != list_of_saved.hashed:
    logging("Fatal error: Checksum failed : \nOrigin hash: " + list_to_save.hashed + "\nSaved hash: " + list_of_saved.hashed + "\n Are you root?")
    sys.exit()
else:
    logging ("Checksum succeeded, the copy is a success\nBegins to send copy over FTP\n")

# Step 5 Backup the DB
# Step 5.1 Create Backup
address = searchline('host')
user = searchline('user')
password = searchline('password')

#checkinstalled('mysql-client')
os.system("mysqldump -h " + address + " -u " + user + " --password=" + password + " --all-databases > " + save_path + '/backup.sql')

# Step 6 Copy to FTP server
# Step 6.1 compress BACKUP
logging ("Compressing Backup...\n")
compress(save_path)
archive = str(save_path + 'WP-BACKUP.tar.gz')
check_saved = checksum(archive)
logging ("Backup compressed, MD5 HASH : " + check_saved + '\n')
# Step 6.2 Connect to FTP server and send it
FTP_host = searchline('FTP_host')
FTP_port = searchline('FTP_port')
FTP_user = searchline('FTP_user')
FTP_password = searchline('FTP_password')
FTP_file = archive
dict = {'ftp' : FTP_host, 'port' : FTP_port, 'user' : FTP_user, 'pass' : FTP_password, 'file' : FTP_file}
transfert(**dict)
logging ("Backup saved on FTP server at " + FTP_host + '\n')

# Step 7 Test the integrity
dict['file'] = "WP-BACKUP.tar.gz"
check_uploaded = FTP_check_integrity(**dict)
logging("Uploaded file's hash is: " + check_uploaded + '\n')
if check_saved == check_uploaded:
    logging("Operation Completed \n")
else:
    logging("FATAL ERROR: Integrity of uploaded file can't be verified \n")
