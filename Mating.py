#!/usr/bin/home/python
import argparse,copy,datetime,logging,os,sys, sqlite3
import numpy as np
import random as rnd
import Settings as sp
from select import select

################################################################################
class Mating:
    def __init__(self, settings):
        self.appLogger=logging.getLogger('sngsw')
        self.appLogger.info("Mating: Run started")
        self.settings=settings
        # Number of species trees replicates/folder to work with
        self.numSpeciesTrees=0
        self.numSpeciesTreesDigits=0
        # Number of fasta per replicate
        self.numFastaFiles=0
        self.numFastaFilesDigits=0
        # Checking the format of the inputted simphy directory
        self.path=os.path.abspath(self.settings.parser.get("general", "simphy_folder"))
        if (self.settings.parser.get("general", "simphy_folder")[-1]=="/"):
            self.projectName=os.path.basename(self.settings.parser.get("general", "simphy_folder")[0:-1])
        else:
            self.projectName=os.path.basename(self.settings.parser.get("general", "simphy_folder"))

        # outgroup
        self.outgroup=self.settings.parser.getboolean("general","outgroup")
        # Prefix of the datafiles that contain the FASTA sequences for
        # its corresponding gene tree.
        self.dataprefix=self.settings.parser.get("general","data_prefix")
        # Number of files to output per genetree
        self.numOutput=self.settings.parser.getint("mating","output-per-individual")
        self.appLogger.debug("Numer of output files: {0}".format(self.numOutput))
        self.output=""

        self.output=os.path.abspath("{0}/{1}/individuals".format(self.path,self.settings.parser.get("general","output_folder")))
        try:
            os.mkdirs(self.output)
            self.appLogger.info("Generating output folder ({0})".format(self.output))
        except:
            self.appLogger.debug("Output folder exists ({0})".format(self.output))

        self.outputmating=os.path.abspath("{0}/{1}/mating".format(self.path,self.settings.parser.get("general","output_folder")))
        try:
            os.mkdirs(self.output)
            self.appLogger.info("Generating output folder ({0})".format(self.output))
        except:
            self.appLogger.debug("Output folder exists ({0})".format(self.output))




    def checkArgs(self):
        self.appLogger.info("Checking SimPhy folder...")
        matingArgsMessageCorrect="Settings are correct, Mating process can be run."
        matingArgsMessageWrong="Something went wrong.\n"
        # Dir exists
        simphydir=os.path.exists(self.path)
        if simphydir:
            self.appLogger.debug("SimPhy folder exists:\t{0}".format(simphydir))
        else:
            matingArgsMessageWrong+="\n\tSimPhy folder does not exist."
            return False, matingArgsMessageWrong

        # List all the things in the project directory
        fileList=os.listdir(os.path.abspath(self.path))
        for index in range(0,len(fileList)):
            fileList[index]=os.path.abspath(os.path.join(self.path,fileList[index]))

        self.command = os.path.join(self.path,"{0}.command".format(self.projectName))
        self.params = os.path.join(self.path,"{0}.params".format(self.projectName))
        self.db = os.path.join(self.path,"{0}.db".format(self.projectName))

        self.appLogger.debug("SimPhy files (command, params, db)")
        self.appLogger.debug("{0}:\t{1}".format(os.path.basename(self.db),self.db in fileList))
        self.appLogger.debug("{0}:\t{1}".format(os.path.basename(self.command),self.command in fileList))
        self.appLogger.debug("{0}:\t{1}".format(os.path.basename(self.params),self.params in fileList))

        simphyfiles=((self.command in fileList) and (self.params in fileList) and(self.db in fileList))

        # check if  command, db, params files
        if not simphyfiles:
            matingArgsMessageWrong+="\n\tSimPhy files do not exist."
            return False, matingArgsMessageWrong

        # check how many of them are dirs
        for item in fileList:
            baseitem=os.path.basename(item)
            if (os.path.isdir(os.path.abspath(item)) and  baseitem.isdigit()):
                self.numSpeciesTrees=self.numSpeciesTrees+1
        self.numSpeciesTreesDigits=len(str(self.numSpeciesTrees))
        # check if at least one

        self.appLogger.debug("Num species trees:\t{0}".format(self.numSpeciesTrees))
        if not (self.numSpeciesTrees>0):
            matingArgsMessageWrong+="\n\tNot enough number of species tree replicates (at least 1):\t{0}".format(self.numSpeciesTrees>0)
            return False, matingArgsMessageWrong

        # Checking output path
        self.appLogger.info("Checking output folder...")
        # Checking output path
        try:
            self.appLogger.info("Creating output folder: {0} ".format(self.output))
            self.output=os.path.abspath(self.output)
            os.mkdir(self.output)
        except:
           self.appLogger.debug("Output folder ({0}) exists. ".format(self.output))

        # Adjusting range of number of possible output files
        if self.numOutput > 2:
            self.numOutput=2
            self.appLogger.warning("Number of output files out of range. Adjusted to maximum number: ".format(self.outputFile))
        if self.numOutput < 1:
            self.numOutput=1
            self.appLogger.warning("Number of output files out of range. Adjusted to minimum number".format(self.outputFile))

        self.filteredSts=self.stWithEvenNumberIndsPerSpecies()
        self.settings.parser.set("general","filtered_ST",self.filteredSts)
        return True, matingArgsMessageCorrect



    def print_configuration(self):
        self.appLogger.debug(\
            "\n\t{0}Configuration...{1}\n\tSimPhy project name:\t{2}\n\tSimPhy path:\t{3}\n\tOutput folder:\t{4}\n\tDataset prefix(es) (INDELible):\t{5}\n\tNumber of species trees replicates/folders:\t{6}".format(\
                mof.BOLD,mof.END,\
                self.projectName,\
                self.path,\
                self.output,\
                self.dataprefix,\
                self.numSpeciesTrees\
            )
        )

    def stWithEvenNumberIndsPerSpecies(self):
        query="select SID from Species_Trees WHERE Ind_per_sp % 2 = 0"
        con = sqlite3.connect(self.db)
        res=con.execute(query).fetchall()
        con.close()
        res=[item for sublist in res for item in sublist]
        return res

    """
    ############################################################################
    #                       Iterationg over STs                                #
    ############################################################################
    """
    def iteratingOverST(self):
        self.appLogger.debug("(class Mating | iteratingOverST() )")

        # iterate over STs
        for indexST in self.filteredSts:
            curReplicatePath="{0}/{1:0{2}d}/".format(self.path,indexST, self.numSpeciesTreesDigits)
            self.appLogger.info("Replicate {0}/{2} ({1})".format(indexST, curReplicatePath,self.numSpeciesTrees))
            self.numFastaFiles=0;numGeneTrees=0
            fileList=os.listdir(curReplicatePath)
            # check composition of the current indexST folder
            for item in fileList:
                if ("{0}_".format(self.dataprefix) in item) and (".fasta" in item):
                    self.numFastaFiles+=1
                if  ("g_trees" in item) and (".trees" in item):
                    numGeneTrees+=1

            self.appLogger.warning("Number of fasta files:\t{0}".format(self.numFastaFiles))
            numGeneTreesDigits=len(str(numGeneTrees))
            self.numFastaFilesDigits=len(str(self.numFastaFiles))
            if (self.numFastaFiles<1): # Do not have fasta files from the given replicate to work, I'll skip it.
                self.appLogger.warning("Replicate {0}({1}): It is not possible to do the mating for this replicate".format(indexST, curReplicatePath))
                self.appLogger.warning("There are no sequences o there is a missmatch between the prefixes and the number of sequences in the folder.")
            if (numGeneTrees<1):
                # I have at least 1 fasta file to work
                self.ending(False,"Trying to mate sequences, but there are no gene tree files to back that up. Please, finish the SimPhy run and try again afterwards.")
            else:
                # I have at least same number of files to work as gene trees
                # it seems that all makes sense
                self.appLogger.debug("Working directly with FASTA files")
                self.appLogger.info("Mating...")

                matingTable=self.generateMatingTable(indexST)
                self.writeMatingTable(matingTable)
                for indexLOC in range(1,self.numFastaFiles+1):
                    self.appLogger.debug("Number of FASTA file: {0}".format(indexLOC))
                    newFolder="{0}/{1:0{2}d}/{3:0{4}d}".format(self.output,\
                        indexST, self.numSpeciesTreesDigits,\
                        indexLOC,self.numFastaFilesDigits\
                    )
                    try:
                        os.makedirs(newFolder)
                    except:
                        self.appLogger.debug("Folder {0} exists.".format(newFolder))
                    seqDict=self.parseMSAFile(indexST,indexLOC)
                    self.mate(matingTable,seqDict)



    def generateMatingTable(self,indexST):
        # missing outgroup
        self.appLogger.info("Connecting to the db...")
        con = sqlite3.connect(self.db)
        query="select SID, Leaves, Ind_per_sp from Species_Trees WHERE SID={0}".format(indexST)
        res=con.execute(query).fetchone()
        con.close()
        indexST=res[0];leaves=res[1];nIndsPerSp=res[2]
        # by default there are no outgroups, if there are, this
        # value will change
        nInds=leaves/2
        if self.outgroup:
            mates+=[(indexST,0,0,0)]
            nInds=(leaves-1)/2
        inds=range(0,nIndsPerSp)
        species=range(1,leaves)
        mates=[]
        self.appLogger.debug("indexST: {0} / inds:{1} ".format(indexST,inds))
        # I'm always assuming there's an outgroup
        for sp in species:
            t=copy.deepcopy(inds)
            while not t==[]:
                p1=0;p2=0
                try:
                    p1=t.pop(rnd.sample(range(0,len(t)),1)[0])
                    p2=t.pop(rnd.sample(range(0,len(t)),1)[0])
                except Exception as e:
                    break
                pair=(indexST,sp,p1,p2)
                mates+=[pair]
                self.appLogger.debug("Pair generated: {0}".format(pair))
        return mates

    def writeMatingTable(self,matingTable):
        # mating table
        # indexST,SP,ind-tip1,ind-tip2
        # If i have outgroups mate info should be in the table already
        self.appLogger.debug("Writing indexes into file...")
        indexFilename="{0}/{1}.{2:0{3}d}.mating".format(self.outputmating,self.projectName, indexST, self.numSpeciesTreesDigits)
        if not os.path.isfile(indexFilename):
            indexFile=open(indexFilename,"w")
            indexFile.write("indexST,indID,speciesID,mateID1,mateID2\n")
            indexFile.close()

        indexFile=open(indexFilename,"a")
        for indexRow in range(0,len(matingTable)):
            indexST=row[0]
            indID=indexRow
            speciesID=row[1]
            mateID1=row[2]
            mateID2=row[3]
            indexFile.write("{0:0{1}d},{2},{3},{4},{5}\n".format(\
            indexST,self.numSpeciesTreesDigits,
                indID,speciesID,mateID1,mateID2))
        indexFile.close()

    def parseMSAFile(self, indexST, indexLOC):
        fastapath="{0}/{1:0{2}d}/{3}_{4:0{5}d}.fasta".format(\
            self.path,\
            indexST,\
            self.numSpeciesTreesDigits,\
            self.dataprefix,\
            indexLOC,\
            self.numFastaFilesDigits)
        fastafile=open(fastapath, 'r')
        lines=fastafile.readlines()
        fastafile.close()
        seqDict=dict()
        description=""; seq=""; tmp="";count=1
        for line in lines:
            if not (line.strip()==''):
                if (count%2==0):
                    seq=line[0:-1].strip()
                    try:
                        test=seqDict[tmp[0]]
                    except:
                        seqDict[tmp[0]]={}

                    try:
                        seqDict[tmp[0]].update({tmp[2]:{\
                            'description':description,\
                            'sequence':seq\
                        }})
                    except:
                        seqDict[tmp[0]][tmp[2]]={}
                        seqDict[tmp[0]].update({tmp[2]:{\
                            'description':description,\
                            'sequence':seq\
                        }})
                    seq=None
                    description=None
                    tmp=None
                else:
                    description=line[0:-1].strip()
                    tmp=description[1:len(description)].split("_")
        return seqDict

    def mateAll(self,matingTable,sequenceDictionary):
        # Proper mating
        originalDict=copy.deepcopy(sequenceDictionary)
        species=originalDict.keys()
        numSeqs=0
        for key in species:
            subspecies=originalDict[key].keys()
            for subkey in subspecies:
                numSeqs+=len(originalDict[key][subkey])

        numInds=np.trunc(numSeqs/2)+1
        currentInd=1
        self.appLogger.debug("Writing {1} individuals from {0} number of sequences.".format(numSeqs,numInds))

        outputFolder="{0}/{1:0{2}d}/{3:0{4}d}".format(self.output,\
            indexST,self.numSpeciesTreesDigits,\
            indexLOC,self.numFastaFilesDigits\
        )
        self.appLogger.debug("Output folder:".format(outputFolder))

        """
        ####################################################################
        # Writing individuals into separate files
        ####################################################################
        """
        for key in species:
            seqDict=copy.deepcopy(originalDict)
            seq1="";des1="";seq2="";des2="";
            if key == "0":
                # For the outgroup
                shortDesc=seqDict[key]["0"]["description"][1:len(seqDict[key]["0"]["description"])]
                des1=">{0}:{1:0{6}d}:{2:0{7}d}:{3}:{4}:{5}".format(self.projectName,\
                    indexST,indexLOC,self.dataprefix,0,shortDesc,\
                    self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                    )
                seq1=seqDict[key]["0"]["sequence"]

                # Writing the outgroup -----------------------------------------
                if (self.numOutput == 1):
                    indFilename="{0}/{1}_{2:0{6}d}_{3:0{7}d}_{4}_{5}.fasta".format(\
                        outputFolder,self.projectName,indexST,indexLOC,\
                        self.dataprefix,0,\
                        self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                    )
                    indFile=open(indFilename, "w")
                    indFile.write("{0}_S1\n{1}\n{2}_S2\n{3}\n".format(des1,seq1,des1,seq1))
                    indFile.close()
                if (self.numOutput == 2):
                    # General file -------------------------------------
                    indFilename="{0}/{1}_{2:0{6}d}_{3:0{7}d}_{4}_{5}.fasta".format(\
                        outputFolder,self.projectName,indexST,indexLOC,\
                        self.dataprefix,0,\
                        self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                    )
                    indFile=open(indFilename, "w")
                    indFile.write("{0}_S1\n{1}\n{2}_S2\n{3}\n".format(des1,seq1,des1,seq1))
                    indFile.close()
                    # Strand 1 -----------------------------------------
                    indFilename="{0}/{1}_{2:0{7}d}_{3:0{8}d}_{4}_{5}_{6}_S1.fasta".format(\
                        outputFolder,self.projectName,indexST,indexLOC,\
                        self.dataprefix,0, shortDesc,\
                        self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                    )
                    indFile=open(indFilename, "w")
                    indFile.write("{0}_S1\n{1}\n".format(des1,seq1))
                    indFile.close()
                    # Strand 2 -----------------------------------------
                    indFilename="{0}/{1}_{2:0{7}d}_{3:0{8}d}_{4}_{5}_{6}_S2.fasta".format(\
                        outputFolder,self.projectName,indexST,indexLOC,\
                        self.dataprefix,0, shortDesc,\
                        self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                    )
                    indFile=open(indFilename, "w")
                    indFile.write("{0}_S2\n{1}\n".format(des1,seq1))
                    indFile.close()

                del seqDict["0"]
            else:
                # for all species except the outgroup
                pairs=indexesDict[key]
                for pair in pairs:
                    # Extracting info from the dictionary
                    currentInd=pair[0];pair1=pair[1]; pair2=pair[2];
                    # Organizing strings
                    self.appLogger.debug("{0}|{1}".format(pair, key))
                    seq1=seqDict[key][pair1]["sequence"]
                    seq2=seqDict[key][pair2]["sequence"]
                    shortDesc1=seqDict[key][pair1]["description"][1:len(seqDict[key][pair1]["description"])]
                    des1=">{0}:{1:0{6}d}:{2:0{7}d}:{3}:{4}:{5}_S1".format(self.projectName,\
                        indexST,indexLOC,self.dataprefix,currentInd,shortDesc1,\
                        self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                    )
                    shortDesc2=seqDict[key][pair2]["description"][1:len(seqDict[key][pair2]["description"])]
                    des2=">{0}:{1:0{6}d}:{2:0{7}d}:{3}:{4}:{5}_S2".format(\
                        self.projectName,indexST,indexLOC,self.dataprefix,\
                        currentInd,shortDesc2,
                        self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                    )

                    if (self.numOutput == 1):
                        indFilename="{0}/{1}_{2:0{6}d}_{3:0{7}d}_{4}_{5}.fasta".format(\
                            outputFolder,self.projectName,indexST,indexLOC,\
                            self.dataprefix,currentInd,\
                            self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                        )
                        indFile=open(indFilename, "w")
                        indFile.write("{0}\n{1}\n{2}\n{3}\n".format(des1,seq1,des2,seq2))
                        indFile.close()
                    if (self.numOutput == 2):
                        # General file -------------------------------------
                        indFilename="{0}/{1}_{2:0{6}d}_{3:0{7}d}_{4}_{5}.fasta".format(\
                            outputFolder,self.projectName,indexST,indexLOC,\
                            self.dataprefix,currentInd,\
                            self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                        )

                        indFile=open(indFilename, "w")
                        indFile.write("{0}\n{1}\n{2}\n{3}\n".format(des1,seq1,des2,seq2))
                        indFile.close()
                        # Strand 1 -----------------------------------------
                        indFilename="{0}/{1}_{2:0{7}d}_{3:0{8}d}_{4}_{5}_{6}_S1.fasta".format(\
                            outputFolder,self.projectName,indexST,indexLOC,\
                            self.dataprefix,currentInd, shortDesc1,\
                            self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                        )

                        indFile=open(indFilename, "w")
                        indFile.write("{0}\n{1}\n".format(des1,seq1))
                        indFile.close()
                        # Strand 2 -----------------------------------------
                        indFilename="{0}/{1}_{2:0{7}d}_{3:0{8}d}_{4}_{5}_{6}_S2.fasta".format(\
                            outputFolder,self.projectName,indexST,indexLOC,\
                            self.dataprefix,currentInd, shortDesc2,\
                            self.numSpeciesTreesDigits,self.numFastaFilesDigits\
                        )

                        indFile=open(indFilename, "w")
                        indFile.write("{0}\n{1}\n".format(des2,seq2))
                        indFile.close()

                    del seqDict[key][pair1]
                    del seqDict[key][pair2]
                if not seqDict[key]=={}:
                    self.appLogger.warning("Number of individuals (sequences) generated per species is odd.")
                    self.appLogger.warning("Sequence {0} from species {1} will not be paired.".format( seqDict[key].keys(), key))
                    for item in seqDict[key].keys():
                        del seqDict[key][item]

        return None
