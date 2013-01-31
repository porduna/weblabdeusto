import traceback
from wlcloud import db

try:
    db.drop_all()
    db.create_all()
except:
    traceback.print_exc()
    print 
    print "Deployment failed. Do you have postgresql installed and the database created?"
    print 
    print "In Ubuntu, for instance, the following steps are required: "
    print "sudo apt-get install postgresql"
    print "sudo -u postgres psql postgres"
    print "  \password postgres"
    print "sudo -u postgres createdb weblab"
    print 

