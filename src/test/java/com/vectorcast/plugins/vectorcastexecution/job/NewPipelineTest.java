package com.vectorcast.plugins.vectorcastexecution.job;

import hudson.model.Item;
import hudson.security.ACL;
import hudson.security.ACLContext;
import hudson.security.Permission;
import jenkins.model.Jenkins;
import net.sf.json.JSONObject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.jvnet.hudson.test.JenkinsRule;
import org.jvnet.hudson.test.MockAuthorizationStrategy;
import org.jvnet.hudson.test.junit.jupiter.WithJenkins;
import org.kohsuke.stapler.StaplerRequest;
import org.kohsuke.stapler.StaplerResponse;
import org.mockito.Mockito;


import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;

@WithJenkins
class NewPipelineTest {

    private static final long USE_LOCAL_IMPORTED_RESULTS = 1;
    private static final long USE_EXTERNAL_IMPORTED_RESULTS = 2;
    private static final String EXTERNAL_RESULT_FILENAME = "archivedResults/project.vcr";

    /** Jenkins Coverage plugin selection. */
    private static final long USE_COVERAGE_PLUGIN = 1;

    /** VectorCAST Coverage plugin selection. */
    private static final long USE_VCC_PLUGIN = 2;

    private static final String PROJECTNAME = "project_vcast_pipeline";

    private JenkinsRule j;

    @BeforeEach
    void beforeEach(JenkinsRule rule) {
        j = rule;
    }

    private NewPipelineJob setupTestBasic(JSONObject jsonForm) throws Exception {
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

            NewPipelineJob job = new NewPipelineJob(request, response);

            assertEquals("project", job.getBaseName());
            job.create();
            assertEquals(PROJECTNAME, job.getProjectName());

            // Pipeline Jobs have no "topProject"
            assertNull(job.getTopProject());

            return job;
        }
    }

    private void checkImportedResults(NewPipelineJob job, long useLocalResults, Boolean useExternalResults, String externalResultsFilename) {
        if (useLocalResults == USE_LOCAL_IMPORTED_RESULTS) {
            assertTrue(job.getUseLocalImportedResults());
        }
        else if (useLocalResults == USE_EXTERNAL_IMPORTED_RESULTS) {
            assertFalse(job.getUseLocalImportedResults());
        }
        assertEquals(useExternalResults, job.getUseExternalImportedResults());
        assertEquals(externalResultsFilename, job.getExternalResultsFilename());
    }

    private void checkAdditionalTools (NewPipelineJob job,
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

    @Test
    void testDefaults() throws Exception {
        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("nodeLabel","Test_Node");

        NewPipelineJob job = setupTestBasic(jsonForm);

        assertTrue(job.getUseStrictTestcaseImport());
        assertFalse(job.getUseCoveragePlugin());
        assertFalse(job.getUseCILicenses());
        assertTrue(job.getUseCBT());
        assertFalse(job.getSingleCheckout());
        assertFalse(job.getUseParameters());
        assertFalse(job.getUseRGW3());
        assertFalse(job.getUseCoverageHistory());
        assertEquals("", job.getSharedArtifactDir());
        assertEquals("", job.getTestInsightsScmTech());
        assertNull(job.getEnvironmentSetup());
        assertNull(job.getExecutePreamble());
        assertNull(job.getEnvironmentTeardown());
        assertNull(job.getPostSCMCheckoutCommands());
        assertEquals("", job.getPipelineSCM());
        assertEquals(0, job.getMaxParallel().longValue());
    }

    @Test
    void testAdditionalTools() throws Exception {
        JSONObject jsonForm = new JSONObject();

        JSONObject jsonCovDisplay  = new JSONObject();
        jsonCovDisplay.put("value", USE_COVERAGE_PLUGIN);

        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("optionClean", true);
        jsonForm.put("coverageDisplayOption", jsonCovDisplay);  // VectorCAST Coverage Plugin
        jsonForm.put("useCoverageHistory", true);
        jsonForm.put("pclpCommand","call lint_my_code.bat");
        jsonForm.put("pclpResultsPattern","lint_results.xml");
        jsonForm.put("TESTinsights_URL","https://teamservices.vector.com/teamareas/pct");
        jsonForm.put("squoreCommand","hello squore test world");
        jsonForm.put("TESTinsights_proxy","TI Proxy 1234@localhost");
        
        NewPipelineJob job = setupTestBasic(jsonForm);
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
        jsonForm.put("coverageDisplayOption", jsonCovDisplay);  // Jenkins Coverage Plugin

        NewPipelineJob job = setupTestBasic(jsonForm);

        assertTrue(job.getUseCoveragePlugin());
    }

    @Test
    void testOptions() throws Exception {
        JSONObject jsonForm = new JSONObject();

        JSONObject jsonCovDisplay  = new JSONObject();
        jsonCovDisplay.put("value", USE_VCC_PLUGIN);

        jsonForm.put("manageProjectName", "project.vcm");
        jsonForm.put("optionClean", true);
        jsonForm.put("nodeLabel","Test_Node");
        jsonForm.put("sharedArtifactDir","/home/jenkins/sharedArtifactDir");
        jsonForm.put("scmSnippet","git 'http://git.com'");
        jsonForm.put("environmentSetup","call setup.bat");
        jsonForm.put("executePreamble","wr_env.bat");
        jsonForm.put("environmentTeardown","close ports");
        jsonForm.put("postSCMCheckoutCommands","chmod a+wr -R *");
        jsonForm.put("coverageDisplayOption",jsonCovDisplay);
        jsonForm.put("maxParallel",10);

        NewPipelineJob job = setupTestBasic(jsonForm);

        assertTrue(job.getUseStrictTestcaseImport());
        assertFalse(job.getUseCILicenses());
        assertTrue(job.getUseCBT());
        assertFalse(job.getSingleCheckout());
        assertFalse(job.getUseParameters());
        assertFalse(job.getUseRGW3());
        assertFalse(job.getUseCoveragePlugin());
        assertFalse(job.getUseCoverageHistory());
        assertNotEquals(-1, job.getSharedArtifactDir().indexOf("/home/jenkins/sharedArtifactDir"));
        assertEquals("git", job.getTestInsightsScmTech());
        assertEquals("call setup.bat", job.getEnvironmentSetup());
        assertEquals("wr_env.bat", job.getExecutePreamble());
        assertEquals("close ports", job.getEnvironmentTeardown());
        assertEquals("chmod a+wr -R *", job.getPostSCMCheckoutCommands());
        assertEquals("git 'http://git.com'", job.getPipelineSCM());
        assertEquals(10, job.getMaxParallel().longValue());
        assertFalse(job.getUseCoveragePlugin());
    }

    @Test
    void testLocalImportedResults() throws Exception {
        JSONObject jsonImportResults  = new JSONObject();
        jsonImportResults.put("value", USE_LOCAL_IMPORTED_RESULTS);

        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("useImportedResults", true);
        jsonForm.put("importedResults", jsonImportResults);

        NewPipelineJob job = setupTestBasic(jsonForm);

        checkImportedResults(job, USE_LOCAL_IMPORTED_RESULTS, false, "");
    }

    @Test
    void testExternalImportedResults() throws Exception {
        JSONObject jsonImportResults  = new JSONObject();
        jsonImportResults.put("value", USE_EXTERNAL_IMPORTED_RESULTS);
        jsonImportResults.put("externalResultsFilename",EXTERNAL_RESULT_FILENAME);

        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "/home/jenkins/vcast/project.vcm");
        jsonForm.put("useImportedResults", true);
        jsonForm.put("importedResults", jsonImportResults);

        NewPipelineJob job = setupTestBasic(jsonForm);

        checkImportedResults(job, USE_EXTERNAL_IMPORTED_RESULTS, true, EXTERNAL_RESULT_FILENAME);
    }

    @Test
    void testGitSCM() throws Exception {
        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "project.vcm");
        jsonForm.put("TESTinsights_URL","https://teamservices.vector.com/teamareas/pct");
        jsonForm.put("scmSnippet","git 'http://git.com'");

        NewPipelineJob job = setupTestBasic(jsonForm);

        assertEquals("git", job.getTestInsightsScmTech());
    }

    @Test
    void testSvnSCM() throws Exception {
        JSONObject jsonForm = new JSONObject();
        jsonForm.put("manageProjectName", "project.vcm");
        jsonForm.put("TESTinsights_URL","https://teamservices.vector.com/teamareas/pct");
        jsonForm.put("scmSnippet","svn 'http://svn.com'");

        NewPipelineJob job = setupTestBasic(jsonForm);

        assertEquals("svn", job.getTestInsightsScmTech());
    }
    
    /* TODO: Use Parameters */
    /* TODO: Specify Job name */
    /* TODO: Multiple jobs with same name */
    /* TODO: MPname without .vcm */
    /* TODO: MPname on network driver abs path \\ */
    /* TODO: MPname on windows abs path */
    /* TODO: MPname on abs path and some SCM */
    /* TODO: use CBT */
    /* TODO: use CI license */
    /* TODO: env sections and post checkout set to "" */
    
    
}

