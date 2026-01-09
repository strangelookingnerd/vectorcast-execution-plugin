package com.vectorcast.plugins.vectorcastexecution.job;

import com.vectorcast.plugins.vectorcastcoverage.VectorCASTPublisher;
import com.vectorcast.plugins.vectorcastexecution.VectorCASTCommand;
import com.vectorcast.plugins.vectorcastexecution.VectorCASTSetup;
import hudson.model.Descriptor;
import hudson.model.Item;
import hudson.plugins.ws_cleanup.PreBuildCleanup;
import hudson.security.ACL;
import hudson.security.ACLContext;
import hudson.security.Permission;
import hudson.tasks.ArtifactArchiver;
import hudson.tasks.BuildWrapper;
import hudson.tasks.Builder;
import hudson.tasks.Publisher;
import hudson.util.DescribableList;
import jenkins.model.Jenkins;
import net.sf.json.JSONObject;

import hudson.tasks.junit.JUnitResultArchiver;
import hudson.plugins.copyartifact.CopyArtifact;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.jvnet.hudson.plugins.groovypostbuild.GroovyPostbuildRecorder;
import org.jvnet.hudson.test.JenkinsRule;
import org.jvnet.hudson.test.MockAuthorizationStrategy;
import org.jvnet.hudson.test.junit.jupiter.WithJenkins;
import org.kohsuke.stapler.StaplerRequest;
import org.kohsuke.stapler.StaplerResponse;
import org.mockito.Mockito;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;

import io.jenkins.plugins.coverage.metrics.steps.CoverageRecorder;
import io.jenkins.plugins.coverage.metrics.steps.CoverageTool;
import io.jenkins.plugins.coverage.metrics.steps.CoverageTool.Parser;
import java.util.List;

@WithJenkins
class NewSingleJobTest {

    private static final String DEFAULT_ARTIFACT_LIST = "**/*.html, xml_data/**/*.xml,"
                + "unit_test_*.txt, **/*.png, **/*.css,"
                + "complete_build.log, *_results.vcr";

    private static final long USE_LOCAL_IMPORTED_RESULTS = 1;
    private static final long USE_EXTERNAL_IMPORTED_RESULTS = 2;
    private static final String EXTERNAL_RESULT_FILENAME = "archivedResults/project.vcr";

    /** Jenkins Coverage plugin selection. */
    private static final long USE_COVERAGE_PLUGIN = 1;

    /** VectorCAST Coverage plugin selection. */
    private static final long USE_VCC_PLUGIN = 2;

    private static final String PROJECTNAME = "project.vcast.single";

    private JenkinsRule j;

    @BeforeEach
    void beforeEach(JenkinsRule rule) {
        j = rule;
    }

    private NewSingleJob setupTestBasic(JSONObject jsonForm) throws Exception {
        try (ACLContext ignored = ACL.as2(ACL.SYSTEM2)) {
            j.jenkins.setSecurityRealm(j.createDummySecurityRealm());
            MockAuthorizationStrategy mockStrategy = new MockAuthorizationStrategy();
            mockStrategy.grant(Jenkins.READ).everywhere().to("devel");
            for (Permission p : Item.PERMISSIONS.getPermissions()) {
                mockStrategy.grant(p).everywhere().to("devel");
            }
            j.jenkins.setAuthorizationStrategy(mockStrategy);

            StaplerRequest request = Mockito.mock(StaplerRequest.class);
            StaplerResponse response = Mockito.mock(StaplerResponse.class);

            when(request.getSubmittedForm()).thenReturn(jsonForm);

            NewSingleJob job = new NewSingleJob(request, response);

            assertEquals("project", job.getBaseName());
            job.create();
            assertEquals(PROJECTNAME, job.getProjectName());
            assertNotNull(job.getTopProject());

            return job;
        }
    }

    private void checkJunitGroovy(DescribableList<Publisher,Descriptor<Publisher>> publisherList, int jUnitIndex, int groovyIndex) {
        // Publisher 1- JUnitResultArchiver
        assertInstanceOf(JUnitResultArchiver.class, publisherList.get(jUnitIndex));
        JUnitResultArchiver jUnit = (JUnitResultArchiver) publisherList.get(jUnitIndex);
        assertEquals("**/test_results_*.xml", jUnit.getTestResults());

        // Publisher 5 - GroovyPostbuildRecorder
        assertInstanceOf(GroovyPostbuildRecorder.class, publisherList.get(groovyIndex));
        GroovyPostbuildRecorder groovyScript = (GroovyPostbuildRecorder) publisherList.get(groovyIndex);
        assertEquals(/*unstable*/1, groovyScript.getBehavior());
    }

    private void checkArchiverList(ArtifactArchiver archiver, String artifactsList) {
        String artifactsFromArchiver = archiver.getArtifacts();
        assertEquals(artifactsList,artifactsFromArchiver);
        assertFalse(archiver.getAllowEmptyArchive());
    }

    private void checkVectorCASTPublisher(DescribableList<Publisher,Descriptor<Publisher>> publisherList, Boolean useCoverageHistory, int vcPubIndex) {
        // Publisher 2 - VectorCASTPublisher
        assertInstanceOf(VectorCASTPublisher.class, publisherList.get(vcPubIndex));
        VectorCASTPublisher vcPublisher = (VectorCASTPublisher) publisherList.get(vcPubIndex);
        assertEquals("**/coverage_results_*.xml", vcPublisher.includes);
        assertEquals(useCoverageHistory, vcPublisher.getUseCoverageHistory());
        assertEquals("**/coverage_results_*.xml", vcPublisher.includes);
        assertEquals(80, vcPublisher.healthReports.getMaxBasisPath());
        assertEquals(0, vcPublisher.healthReports.getMinBasisPath());
        assertEquals(100, vcPublisher.healthReports.getMaxStatement());
        assertEquals(0, vcPublisher.healthReports.getMinStatement());
        assertEquals(70, vcPublisher.healthReports.getMaxBranch());
        assertEquals(0, vcPublisher.healthReports.getMinBranch());
        assertEquals(80, vcPublisher.healthReports.getMaxFunction());
        assertEquals(0, vcPublisher.healthReports.getMinFunction());
        assertEquals(80, vcPublisher.healthReports.getMaxFunctionCall());
        assertEquals(0, vcPublisher.healthReports.getMinFunctionCall());
        assertEquals(80, vcPublisher.healthReports.getMaxMCDC());
        assertEquals(0, vcPublisher.healthReports.getMinMCDC());
    }

    private void checkCoveragePlugin(DescribableList<Publisher,Descriptor<Publisher>> publisherList, int pubListIndex) {
        // Publisher 2 - CoverageRecorder
        assertInstanceOf(CoverageRecorder.class, publisherList.get(pubListIndex));
        CoverageRecorder publisher = (CoverageRecorder) publisherList.get(pubListIndex);

        // CoverageRecorder > CoverageTool
        List<CoverageTool> coverageToolsList = publisher.getTools();
        assertEquals(1, coverageToolsList.size());
        assertInstanceOf(CoverageTool.class, coverageToolsList.get(0));
        CoverageTool coverageTool = coverageToolsList.get(0);

        assertEquals("xml_data/cobertura/coverage_results*.xml", coverageTool.getPattern());
        assertEquals(Parser.VECTORCAST, coverageTool.getParser());
    }

    private void checkBuildWrappers(NewSingleJob job, int builderSize){
        // Check build wrappers...
        DescribableList<BuildWrapper, Descriptor<BuildWrapper>> bldWrappersList = job.getTopProject().getBuildWrappersList();
        assertEquals(builderSize, bldWrappersList.size());
        BuildWrapper wrapper = bldWrappersList.get(0);
        assertInstanceOf(PreBuildCleanup.class, wrapper);
        PreBuildCleanup cleanup = (PreBuildCleanup)wrapper;
        assertTrue(cleanup.getDeleteDirs());
    }

    private void checkBuildAction (NewSingleJob job, Boolean checkBuildAction) {
        // Check build actions...
        DescribableList<Builder,Descriptor<Builder>> bldrsList = job.getTopProject().getBuildersList();

        if (checkBuildAction) {
            assertEquals(3, bldrsList.size());
            assertInstanceOf(CopyArtifact.class, bldrsList.get(0));
            assertInstanceOf(VectorCASTSetup.class, bldrsList.get(1));
            assertInstanceOf(VectorCASTCommand.class, bldrsList.get(2));
        } else {
            assertEquals(2, bldrsList.size());
            assertInstanceOf(VectorCASTSetup.class, bldrsList.get(0));
            assertInstanceOf(VectorCASTCommand.class, bldrsList.get(1));
        }
    }

    private void checkImportedResults(NewSingleJob job, long useLocalResults, Boolean useExternalResults, String externalResultsFilename) {
        if (useLocalResults == USE_LOCAL_IMPORTED_RESULTS) {
            assertTrue(job.getUseLocalImportedResults());
        }
        else if (useLocalResults == USE_EXTERNAL_IMPORTED_RESULTS) {
            assertFalse(job.getUseLocalImportedResults());
        }
        assertEquals(useExternalResults, job.getUseExternalImportedResults());
        assertEquals(externalResultsFilename, job.getExternalResultsFilename());
    }

    private void checkAdditionalTools (NewSingleJob job,
            final String squoreCommand,
            final String pclpCommand,
            final String pclpResultsPattern,
            final String testInsightsUrl,
            final String tiProxy) {

        assertEquals(squoreCommand, job.getSquoreCommand());
        assertEquals(pclpCommand, job.getPclpCommand());
        assertEquals(pclpResultsPattern, job.getPclpResultsPattern());
        assertEquals(testInsightsUrl, job.getTestInsightsUrl());
        assertEquals(tiProxy, job.getTestInsightsProxy());
    }

    private void checkOptions (NewSingleJob job,
                Boolean optionExecutionReport,
                Boolean optionUseReporting,
                Boolean useCiLicense,
                Boolean useStrictTestcaseImport,
                Boolean useRGW3,
                Boolean useImportedResults,
                Boolean useCoverageHistory) {

        assertEquals(optionExecutionReport, job.getOptionExecutionReport());
        assertEquals(optionUseReporting, job.getOptionUseReporting());
        assertEquals(useCiLicense, job.getUseCILicenses());
        assertEquals(useStrictTestcaseImport, job.getUseStrictTestcaseImport());
        assertEquals(useRGW3, job.getUseRGW3());
        assertEquals(useImportedResults, job.getUseImportedResults());
        assertEquals(useCoverageHistory, job.getUseCoverageHistory());
    }

    @Test
    void testBasic() throws Exception {
        JSONObject jsonForm = new JSONObject();

        JSONObject jsonCovDisplay  = new JSONObject();
        jsonCovDisplay.put("value", USE_VCC_PLUGIN);

        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("optionClean", true);
        jsonForm.put("coverageDisplayOption", jsonCovDisplay);
        jsonForm.put("optionExecutionReport", true);
        jsonForm.put("useStrictTestcaseImport", true);

        NewSingleJob job = setupTestBasic(jsonForm);

        // Check publishers...
        DescribableList<Publisher,Descriptor<Publisher>> publisherList = job.getTopProject().getPublishersList();
        assertEquals(4, publisherList.size());

        // Publisher 0 - ArtifactArchiver
        assertInstanceOf(ArtifactArchiver.class, publisherList.get(0));
        ArtifactArchiver archiver = (ArtifactArchiver)publisherList.get(0);

        checkBuildWrappers(job, 1);
        checkBuildAction(job,false);
        checkArchiverList(archiver, DEFAULT_ARTIFACT_LIST);
        checkJunitGroovy(publisherList, 1, 3);
        checkVectorCASTPublisher(publisherList, false, 2);
    }

    @Test
    void testAdditionalTools() throws Exception {
        JSONObject jsonForm = new JSONObject();
        JSONObject jsonCovDisplay  = new JSONObject();
        jsonCovDisplay.put("value", USE_VCC_PLUGIN);

        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("optionClean", true);
        jsonForm.put("coverageDisplayOption", jsonCovDisplay);  // VectorCAST Coverage Plugin
        jsonForm.put("useCoverageHistory", true);
        jsonForm.put("pclpCommand","call lint_my_code.bat");
        jsonForm.put("pclpResultsPattern","lint_results.xml");
        jsonForm.put("TESTinsights_URL","https://teamservices.vector.com/teamareas/pct");
        jsonForm.put("squoreCommand","hello squore test world");
        jsonForm.put("TESTinsights_proxy","TI Proxy 1234@localhost");

        NewSingleJob job = setupTestBasic(jsonForm);

        // Check publishers...
        DescribableList<Publisher,Descriptor<Publisher>> publisherList = job.getTopProject().getPublishersList();
        assertEquals(5, publisherList.size());

        // Publisher 0 - ArtifactArchiver
        assertInstanceOf(ArtifactArchiver.class, publisherList.get(0));
        ArtifactArchiver archiver = (ArtifactArchiver)publisherList.get(0);

        String addToolArtifacts = DEFAULT_ARTIFACT_LIST;
        addToolArtifacts += ", lint_results.xml";
        addToolArtifacts += ", TESTinsights_Push.log";

        checkBuildWrappers(job, 2);
        checkBuildAction(job,false);
        checkArchiverList(archiver, addToolArtifacts);
        checkJunitGroovy(publisherList,2,4);
        checkVectorCASTPublisher(publisherList, true, 3);
        checkAdditionalTools(job,
                "hello squore test world",
                "call lint_my_code.bat",
                "lint_results.xml",
                "https://teamservices.vector.com/teamareas/pct",
                "TI Proxy 1234@localhost");
    }

    @Test
    void testCoveragePlugin() throws Exception {
        JSONObject jsonForm = new JSONObject();

        JSONObject jsonCovDisplay  = new JSONObject();
        jsonCovDisplay.put("value", USE_COVERAGE_PLUGIN);

        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("optionClean", true);
        jsonForm.put("coverageDisplayOption", jsonCovDisplay);  // Jenkins Coverage Plugin
        jsonForm.put("useCoverageHistory", false);  // VectorCAST Coverage Plugin
        jsonForm.put("pclpCommand","call lint_my_code.bat");
        jsonForm.put("pclpResultsPattern","lint_results.xml");
        jsonForm.put("TESTinsights_URL","https://teamservices.vector.com/teamareas/pct");

        NewSingleJob job = setupTestBasic(jsonForm);

        // Check publishers...
        DescribableList<Publisher,Descriptor<Publisher>> publisherList = job.getTopProject().getPublishersList();
        assertEquals(6, publisherList.size());

        // Publisher 0 - ArtifactArchiver
        assertInstanceOf(ArtifactArchiver.class, publisherList.get(0));
        ArtifactArchiver archiver = (ArtifactArchiver)publisherList.get(0);

        String addToolArtifacts = DEFAULT_ARTIFACT_LIST;
        addToolArtifacts += ", lint_results.xml";
        addToolArtifacts += ", TESTinsights_Push.log";

        checkBuildWrappers(job, 2);
        checkBuildAction(job,false);
        checkArchiverList(archiver, addToolArtifacts);
        checkJunitGroovy(publisherList, 2, 5);
        checkCoveragePlugin(publisherList, 4);
    }

    @Test
    void testLocalImportedResults() throws Exception {
        JSONObject jsonImportResults  = new JSONObject();
        jsonImportResults.put("value", USE_LOCAL_IMPORTED_RESULTS);

        JSONObject jsonCovDisplay  = new JSONObject();
        jsonCovDisplay.put("value", USE_COVERAGE_PLUGIN);

        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("optionClean", true);
        jsonForm.put("coverageDisplayOption", jsonCovDisplay);
        jsonForm.put("useImportedResults", true);
        jsonForm.put("importedResults", jsonImportResults);

        NewSingleJob job = setupTestBasic(jsonForm);

        // Check publishers...
        DescribableList<Publisher,Descriptor<Publisher>> publisherList = job.getTopProject().getPublishersList();
        assertEquals(5, publisherList.size());

        // Publisher 0 - ArtifactArchiver
        assertInstanceOf(ArtifactArchiver.class, publisherList.get(0));
        ArtifactArchiver archiver = (ArtifactArchiver)publisherList.get(0);

        checkBuildWrappers(job, 1);
        checkBuildAction(job, true);
        checkArchiverList(archiver, DEFAULT_ARTIFACT_LIST);
        checkJunitGroovy(publisherList, 1, 4);
        checkCoveragePlugin(publisherList, 3);
        checkImportedResults(job, USE_LOCAL_IMPORTED_RESULTS, false, "");
    }

    @Test
    void testExternalImportedResults() throws Exception {
        JSONObject jsonImportResults  = new JSONObject();
        jsonImportResults.put("value", USE_EXTERNAL_IMPORTED_RESULTS);
        jsonImportResults.put("externalResultsFilename",EXTERNAL_RESULT_FILENAME);

        JSONObject jsonCovDisplay  = new JSONObject();
        jsonCovDisplay.put("value", USE_COVERAGE_PLUGIN);

        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("optionClean", true);
        jsonForm.put("coverageDisplayOption", jsonCovDisplay);
        jsonForm.put("useImportedResults", true);
        jsonForm.put("importedResults", jsonImportResults);

        NewSingleJob job = setupTestBasic(jsonForm);

        // Check publishers...
        DescribableList<Publisher,Descriptor<Publisher>> publisherList = job.getTopProject().getPublishersList();
        assertEquals(5, publisherList.size());

        // Publisher 0 - ArtifactArchiver
        assertInstanceOf(ArtifactArchiver.class, publisherList.get(0));
        ArtifactArchiver archiver = (ArtifactArchiver)publisherList.get(0);

        checkBuildWrappers(job, 1);
        checkBuildAction(job,false);
        checkArchiverList(archiver, DEFAULT_ARTIFACT_LIST);
        checkJunitGroovy(publisherList, 1, 4);
        checkCoveragePlugin(publisherList, 3);
        checkImportedResults(job, USE_EXTERNAL_IMPORTED_RESULTS, true, EXTERNAL_RESULT_FILENAME);
    }

    @Test
    void testDefaultOptions() throws Exception {
        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");

        NewSingleJob job = setupTestBasic(jsonForm);

        checkOptions (job, true, true, false, true, false, false, false);
    }

    @Test
    void testFalseOptions() throws Exception {
        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("optionExecutionReport", false);
        jsonForm.put("optionUseReporting", false);
        jsonForm.put("useCiLicense",false);
        jsonForm.put("useStrictTestcaseImport", false);
        jsonForm.put("useRGW3",false);
        jsonForm.put("useImportedResults", false);
        jsonForm.put("useCoverageHistory", false);

        NewSingleJob job = setupTestBasic(jsonForm);

        checkOptions (job, false, false, false, false, false, false, false);
    }

    @Test
    void testTrueOptions() throws Exception {
        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("optionExecutionReport", true);
        jsonForm.put("optionUseReporting", true);
        jsonForm.put("useCiLicense",true);
        jsonForm.put("useStrictTestcaseImport", true);
        jsonForm.put("useRGW3",true);
        jsonForm.put("useImportedResults", true);
        jsonForm.put("useCoverageHistory", true);

        // cant use Jenkins Coverage with useCoverageHistory
        JSONObject jsonCovDisplay  = new JSONObject();
        jsonCovDisplay.put("value", USE_VCC_PLUGIN);

        jsonForm.put("coverageDisplayOption", jsonCovDisplay);

        NewSingleJob job = setupTestBasic(jsonForm);

        checkOptions (job, true, true, true, true, true, true, true);
    }

    /* TODO: Figure out how to add SCM to be parserd*/
    /* TODO: TestInsights project name: env.JOB_BASE_NAME */
    /* TODO: Specify Job name */
    /* TODO: Multiple jobs with same name */
    /* TODO: MPname set to none */
    /* TODO: MPname without .vcm */
    /* TODO: MPname on network driver abs path \\ */
    /* TODO: MPname on windows abs path */
    /* TODO: MPname on abs path and some SCM */
    /* TODO: use CI license */
    /* TODO: Unix env sections */
    /* TODO: Label not set */
    /* TODO: Windows env sections */
    /* TODO: Post checkout set to "" */
    /* TODO: htmlOrText set to text */
    /* TODO: use Imported results, extFname set to none*/
    /* TODO: different groovy script behaviors */

/*
    @Test
    void testGitSCM() throws Exception {
        JSONObject jsonUserRemoteConfig = new JSONObject();
        jsonUserRemoteConfig.put("url","https://github.com/TimSVector/PointOfSales_v2.git");
        jsonUserRemoteConfig.put("includeUser","false");
        jsonUserRemoteConfig.put("credentialsId","credentialsId");
        jsonUserRemoteConfig.put("name","");
        jsonUserRemoteConfig.put("refspec","");

        JSONObject jsonBranches = new JSONObject();
        jsonBranches.put("name","master");

        JSONObject jsonSCM = new JSONObject();
        jsonSCM.put("value","1");
        jsonSCM.put("stapler-class","hudson.plugins.git.GitSCM");
        jsonSCM.put("$class","hudson.plugins.git.GitSCM");
        jsonSCM.put("userRemoteConfigs",jsonUserRemoteConfig);
        jsonSCM.put("branches",jsonBranches);
        jsonSCM.put("","auto");

        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("TESTinsights_URL","https://teamservices.vector.com/teamareas/pct");
        jsonForm.put("scm", jsonSCM);

        NewSingleJob job = setupTestBasic(jsonForm);

        assertEquals("git", job.getTestInsightsScmTech());
    }

    @Test
    void testSvnSCM() throws Exception {
        JSONObject jsonSCM  = new JSONObject();
        jsonSCM.put("value",loadSvnRepo());

        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("TESTinsights_URL","https://teamservices.vector.com/teamareas/pct");
        jsonForm.put("scm", jsonSCM);

        NewSingleJob job = setupTestBasic(jsonForm,"Subversion");

        assertEquals("svn", job.getTestInsightsScmTech());
    }
*/
}
