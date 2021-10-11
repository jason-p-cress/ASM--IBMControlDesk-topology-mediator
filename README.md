# ASM--IBMControlDesk-topology-mediator

This is an example on how to create a file observer file of CI objects and relationships from
IBM Control Desk's REST API.

# Configuration:

1. Add your ICD server url, API username, and password in the config/icdserver.conf file.
2. The number of CI records to fetch per call is configurable in the config/getICDData.props file.
   Default is 500 records per API call.

	ciFetchLimit=500

3. A mapping file exists that will map the CI CLASSSTRUCTUREID attribute to an ASM entityType.
   This file is located under config/entitytype-mapping.conf and is in the format:
   
      CLASSSTRUCTUREID,entityType

4. A mapping file exists that allows you to map a CI relationship RELATIONNUM to an ASM edgeType.
   This file is located under the config/relationship-mapping.conf and is in the format:

      RELATIONNUM,edgeType

# Running the topology mediation:

1. After configuring the relevant config files, simply run the bin/getICDData.py script. The 
   script will consult the ICD REST interface and create a file observer file that will be
   saved under the file-observer-file directory with the date.

2. Copy the created file observer file to the ASM file observer directory and ingest the file.


