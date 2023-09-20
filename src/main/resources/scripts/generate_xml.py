#
# The MIT License
#
# Copyright 2016 Vector Software, East Greenwich, Rhode Island USA
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

from __future__ import print_function

import os
from datetime import datetime
try:
    from html import escape
except ImportError:
    # html not standard module in Python 2.
    from cgi import escape
import sys
# Later version of VectorCAST have renamed to Unit Test API
# Try loading the newer (renamed) version first and fall back
# to the older.
try:
    from vector.apps.DataAPI.unit_test_api import UnitTestApi
    from vector.apps.DataAPI.unit_test_models import TestCase
except:
    from vector.apps.DataAPI.api import Api as UnitTestApi
    from vector.apps.DataAPI.models import TestCase

try:
    from vector.apps.DataAPI.vcproject_api import VCProjectApi
except:
    pass

from vector.apps.DataAPI.cover_api import CoverApi
from vector.apps.ReportBuilder.custom_report import fmt_percent
from operator import attrgetter
from vector.enums import COVERAGE_TYPE_TYPE_T
import hashlib 
import traceback
import parse_traceback
import tee_print
from safe_open import open
from pprint import pprint
try:
    from vector.apps.ReportBuilder.custom_report import CustomReport
except:
    pass

import re
 
def dummy(*args, **kwargs):
    return None

##########################################################################
# This class generates the XML (JUnit based) report for the overall
# (Emma based) report for Coverage
#
class BaseGenerateXml(object):
    def __init__(self, FullManageProjectName, verbose):
        projectName = os.path.splitext(os.path.basename(FullManageProjectName))[0]
        self.manageProjectName = projectName
        self.cover_report_name = os.path.join("xml_data","coverage_results_"+ self.manageProjectName + ".xml")
        self.unit_report_name = os.path.join("xml_data","test_results_"+ self.manageProjectName + ".xml")
        self.verbose = verbose
        self.using_cover = False
        self.has_sfp_enabled = False
        self.print_exc = False
        
        # get the VC langaguge and encoding
        self.encFmt = 'utf-8'
        from vector.apps.DataAPI.configuration import vcastqt_global_options
        self.lang = vcastqt_global_options.get('Translator','english')
        if self.lang == "english":
            self.encFmt = "utf-8"
        if self.lang == "japanese":
            self.encFmt = "shift-jis"
        if self.lang == "chinese":
            self.encFmt = "GBK"
        
#
# BaseGenerateXml - calculate coverage value
#
    def calc_cov_values(self, x, y):
        column = ''
        if y == 0:
            column = None
        else:
            column = '%s%% (%d / %d)' % (fmt_percent(x, y), x, y)
        return column

    def convertTcStatus(self, status):
        convertDict = { 'TCR_STATUS_OK' : 'Testcase passed',
                        'TCR_STRICT_IMPORT_FAILED' : 'Strict Testcase Import Failure',
                        'TCR_MAXIMUM_VARY_EXCEEDED' : 'Maximum varied parameters exceeded',
                        'TCR_EMPTY_TEST_CASES' : 'Empty testcase',
                        'TCR_NO_EXPECTED_VALUES' : 'No expected values',
                        'TCR_NO_EXPECTED_RETURN' : 'No expected return value',
                        'TCR_NO_SLOTS' : 'Compound with no slot',
                        'TCR_ZERO_ITERATIONS' : 'Compound with zero slot',
                        'TCR_RECURSIVE_COMPOUND' : 'Recursive Compound Test',
                        'TCR_COMMON_COMPOUND_CONTAINING_SPECIALIZED' : 'Non-specialized compound containing specialized testcases',
                        'TCR_HIDING_EXPECTED_RESULTS' : 'Hiding expected results',
                        'TCR_MAX_STRING_LENGTH_EXCEEDED' : 'Maximum string length exceeded',
                        'TCR_MAX_FILE_COUNT_EXCEEDED' : 'Maximum file count exceeded',
                        'TCR_TIMEOUT_EXCEEDED' : 'Testcase timeout',
                        'TCR_INTERNAL_ERROR' : 'Internal VectorCAST Error'
                      }
        return convertDict[str(status)]

    def convertExecStatus(self, status):
        convertDict = { 'EXEC_SUCCESS_PASS':'Testcase passed',
                        'EXEC_SUCCESS_FAIL':'Testcase failed',
                        'EXEC_SUCCESS_NONE':'No expected results',
                        'EXEC_EXECUTION_FAILED':'Testcase failed to run to completion (possible testcase timeout)',
                        'EXEC_ABORTED':'User aborted testcase',
                        'EXEC_TIMEOUT_EXCEEDED':'Testcase timeout',
                        'EXEC_VXWORKS_LOAD_ERROR':'VxWorks load error',
                        'EXEC_USER_CODE_COMPILE_FAILED':'User code failed to compile',
                        'EXEC_COMPOUND_ONLY':'Compound only test case',
                        'EXEC_STRICT_IMPORT_FAILED':'Strict Testcase Import Failure',
                        'EXEC_MACRO_NOT_FOUND':'Macro not found',
                        'EXEC_SYMBOL_OR_MACRO_NOT_FOUND':'Symbol or macro not found',
                        'EXEC_SYMBOL_OR_MACRO_TYPE_MISMATCH':'Symbol or macro type mismatch',
                        'EXEC_MAX_VARY_EXCEEDED':'Maximum varied parameters exceeded',
                        'EXEC_COMPOUND_WITH_NO_SLOTS':'Compound with no slot',
                        'EXEC_COMPOUND_WITH_ZERO_ITERATIONS':'Compound with zero slot',
                        'EXEC_STRING_LENGTH_EXCEEDED':'Maximum string length exceeded',
                        'EXEC_FILE_COUNT_EXCEEDED':'Maximum file count exceeded',
                        'EXEC_EMPTY_TESTCASE':'Empty testcase',
                        'EXEC_NO_EXPECTED_RETURN':'No expected return value',
                        'EXEC_NO_EXPECTED_VALUES':'No expected values',
                        'EXEC_CSV_MAP':'CSV Map',
                        'EXEC_DRIVER_DATA_COMPILE_FAILED':'Driver data failed to compile',
                        'EXEC_RECURSIVE_COMPOUND':'Recursive Compound Test',
                        'EXEC_SPECIALIZED_COMPOUND_CONTAINING_COMMON':'Specialized compound containing non-specialized testcases',
                        'EXEC_COMMON_COMPOUND_CONTAINING_SPECIALIZED':'Non-specialized compound containing specialized testcases',
                        'EXEC_HIDING_EXPECTED_RESULTS':'Hiding expected results',
                        'INVALID_TEST_CASE':'Invalid Test Case'
                       }
        try:                  
            s = convertDict[str(status)]
        except:
            s = convertDict[status]
        return s

    
#
# BaseGenerateXml - create coverage data object for given metrics entry
# for coverage report
#
    def add_coverage(self, is_unit, unit_or_func, metrics, cov_type):
        cov_type_str = str(cov_type)
        entry = {}
        entry["statement"] = None
        entry["branch"] = None
        entry["mcdc"] = None
        entry["basispath"] = None
        entry["function"] = None
        entry["functioncall"] = None

        if self.has_function_coverage:
            if is_unit:
                (total_funcs, funcs_covered) = unit_or_func.cover_data.functions_covered
                entry["function"] = self.calc_cov_values(funcs_covered, total_funcs)
            else:
                if unit_or_func.has_covered_objects:
                    entry["function"] = '100% (1 / 1)'
                else:
                    entry["function"] = '0% (0 / 1)'
                    
        if self.has_call_coverage:
            entry["functioncall"] = self.calc_cov_values(metrics.max_covered_function_calls, metrics.function_calls)
            
        if self.verbose:
            print("Coverage Type:", cov_type_str)
            

        if 'NONE' in cov_type_str:
            return entry         
        
        if "MCDC" in cov_type_str:
            entry["branch"] = self.calc_cov_values(metrics.max_covered_mcdc_branches, metrics.mcdc_branches)
            if not self.simplified_mcdc:
                entry["mcdc"] = self.calc_cov_values(metrics.max_covered_mcdc_pairs, metrics.mcdc_pairs)
        if "BASIS_PATH" in cov_type_str:
            (cov,total) = unit_or_func.basis_paths_coverage
            entry["basis_path"] = self.calc_cov_values(cov, total)
        if "STATEMENT" in cov_type_str:
            entry["statement"] = self.calc_cov_values(metrics.max_covered_statements, metrics.statements)
        if "BRANCH" in cov_type_str:
            entry["branch"] = self.calc_cov_values(metrics.max_covered_branches, metrics.branches)
        if "FUNCTION_FUNCTION_CALL" in cov_type_str:
            entry["functioncall"] = self.calc_cov_values(metrics.max_covered_function_calls, metrics.function_calls)
                        
        return entry
#
# BaseGenerateXml - write the units to the coverage file
#
    def write_cov_units(self):
    
        self.reported_units = {}
        
        for unit in self.our_units:
            unit_name = unit["unit"].name
            if unit_name in self.reported_units.keys():
                self.reported_units[unit_name] += 1
                unit_name = unit_name + "'%d" % self.reported_units[unit_name]
            else:
                self.reported_units[unit_name] = 0
                
            self.fh_data += ('        <unit name="%s">\n' % escape(unit_name, quote=False))
            if unit["coverage"]["statement"]:
                self.fh_data += ('          <coverage type="statement, %%" value="%s"/>\n' % unit["coverage"]["statement"])
            if unit["coverage"]["branch"]:
                self.fh_data += ('          <coverage type="branch, %%" value="%s"/>\n' % unit["coverage"]["branch"])
            if unit["coverage"]["mcdc"]:
                self.fh_data += ('          <coverage type="mcdc, %%" value="%s"/>\n' % unit["coverage"]["mcdc"])
            if unit["coverage"]["basispath"]:
                self.fh_data += ('          <coverage type="basispath, %%" value="%s"/>\n' % unit["coverage"]["basispath"])
            if unit["coverage"]["function"]:
                self.fh_data += ('          <coverage type="function, %%" value="%s"/>\n' % unit["coverage"]["function"])
            if unit["coverage"]["functioncall"]:
                self.fh_data += ('          <coverage type="functioncall, %%" value="%s"/>\n' % unit["coverage"]["functioncall"])
            self.fh_data += ('          <coverage type="complexity, %%" value="0%% (%s / 0)"/>\n' % unit["complexity"])

            for func in unit["functions"]:
                if not self.using_cover:
                    func_name = escape(func["func"].name, quote=True)
                    self.fh_data += ('          <subprogram name="%s">\n' % func_name)
                else:
                    func_name = escape(func["func"].display_name, quote=True)
                    self.fh_data += ('          <subprogram name="%s">\n' % func_name)
                if func["coverage"]["statement"]:
                    self.fh_data += ('            <coverage type="statement, %%" value="%s"/>\n' % func["coverage"]["statement"])
                if func["coverage"]["branch"]:
                    self.fh_data += ('            <coverage type="branch, %%" value="%s"/>\n' % func["coverage"]["branch"])
                if func["coverage"]["mcdc"]:
                    self.fh_data += ('            <coverage type="mcdc, %%" value="%s"/>\n' % func["coverage"]["mcdc"])
                if func["coverage"]["basispath"]:
                    self.fh_data += ('            <coverage type="basispath, %%" value="%s"/>\n' % func["coverage"]["basispath"])
                if func["coverage"]["function"]:
                    self.fh_data += ('            <coverage type="function, %%" value="%s"/>\n' % func["coverage"]["function"])
                if func["coverage"]["functioncall"]:
                    self.fh_data += ('            <coverage type="functioncall, %%" value="%s"/>\n' % func["coverage"]["functioncall"])
                self.fh_data += ('            <coverage type="complexity, %%" value="0%% (%s / 0)"/>\n' % func["complexity"])

                self.fh_data += ('          </subprogram>\n')
            self.fh_data += ('        </unit>\n')

#
# BaseGenerateXml - calculate 'grand total' coverage values for coverage report
#
    def grand_total_coverage(self, cov_type):
        cov_type_str = str(cov_type)

        entry = {}
        entry["statement"] = None
        entry["branch"] = None
        entry["mcdc"] = None
        entry["basispath"] = None
        entry["function"] = None
        entry["functioncall"] = None
        
        if self.has_function_coverage:
            entry["function"] = self.calc_cov_values(self.grand_total_max_covered_functions, self.grand_total_max_coverable_functions)
        if self.has_call_coverage:
            entry["functioncall"] = self.calc_cov_values(self.grand_total_max_covered_function_calls, self.grand_total_function_calls)
            
        if 'NONE' in cov_type_str:
            return entry
            
        if "MCDC" in cov_type_str:
            entry["branch"] = self.calc_cov_values(self.grand_total_max_mcdc_covered_branches, self.grand_total_mcdc_branches)
            if not self.simplified_mcdc:
                entry["mcdc"] = self.calc_cov_values(self.grand_total_max_covered_mcdc_pairs, self.grand_total_mcdc_pairs)
        if "BASIS_PATH" in cov_type_str:
            entry["basis_path"] = self.calc_cov_values(self.grand_total_cov_basis_path, self.grand_total_total_basis_path)
        if "STATEMENT" in cov_type_str:
            entry["statement"] = self.calc_cov_values(self.grand_total_max_covered_statements, self.grand_total_statements)
        if "BRANCH" in cov_type_str:
            entry["branch"] = self.calc_cov_values(self.grand_total_max_covered_branches, self.grand_total_branches)
        if "FUNCTION_FUNCTION_CALL" in cov_type_str:
            entry["functioncall"] = self.calc_cov_values(self.grand_total_max_covered_function_calls, self.grand_total_function_calls)

        return entry

#
# BaseGenerateXml - generate the formatted timestamp to write to the coverage file
#
    def get_timestamp(self):
        dt = datetime.now()
        hour = dt.hour
        if hour > 12:
            hour -= 12
        return dt.strftime('%d %b %Y  @HR@:%M:%S %p').upper().replace('@HR@', str(hour))

#
# BaseGenerateXml - start writing to the coverage file
#
    def start_cov_file(self):

        self.fh_data = ""
        self.fh_data += ('<!-- VectorCAST/Jenkins Integration, Generated %s -->\n' % self.get_timestamp())
        self.fh_data += ('<report>\n')
        self.fh_data += ('  <version value="3"/>\n')

#
# BaseGenerateXml - write the end of the coverage file and close it
#
    def end_cov_file(self):
        self.fh_data += ('</report>')
        with open(self.cover_report_name,"w") as fd:
            try:
                fd.write(self.fh_data)
            except TypeError:
                s = unicode(self.fh_data, self.encFmt)
                fd.write(s)
#
# BaseGenerateXml - write the end of the coverage file and close it
#
    def end_cov_file_environment(self, useEnvs = True):
        self.fh_data += ('      </environment>\n')
        self.fh_data += ('    </all>\n')
        self.fh_data += ('  </data>\n')
        self.end_cov_file()
#
# BaseGenerateXml the XML Modified 'Emma' coverage data
#
    def hasFunctionCoverage(self, cov_types):
        func_cov_types = [COVERAGE_TYPE_TYPE_T.FUNCTION_COVERAGE, COVERAGE_TYPE_TYPE_T.FUNCTION_FUNCTION_CALL, COVERAGE_TYPE_TYPE_T.STATEMENT_FUNCTION_CALL, COVERAGE_TYPE_TYPE_T.STATEMENT_BRANCH_FUNCTION_CALL, COVERAGE_TYPE_TYPE_T.STATEMENT_MCDC_FUNCTION_CALL]
        
        for cov_type in cov_types:
            if cov_type in func_cov_types:
                return True
                
        return False

    def hasAnyCov(self, srcFile):
        try:
            metrics = srcFile.metrics
        except:
            metrics = srcFile.cover_metrics
            
        covTotals = (
            metrics.max_covered_functions + 
            metrics.max_uncovered_branches +
            metrics.max_uncovered_function_calls +
            metrics.max_uncovered_functions +
            metrics.max_uncovered_mcdc_branches +
            metrics.max_uncovered_mcdc_pairs + 
            metrics.max_uncovered_statements )

        return covTotals > 0

#
# BaseGenerateXml the XML Modified 'Emma' coverage data
#
    def _generate_cover(self, cov_type):

        self.num_functions = 0

        self.simplified_mcdc = self.api.environment.get_option("VCAST_SIMPLIFIED_CONDITION_COVERAGE")
        self.our_units = []
        self.has_call_coverage = False
        self.has_function_coverage = False
        self.grand_total_complexity = 0

        self.grand_total_max_covered_branches = 0
        self.grand_total_branches = 0
        self.grand_total_max_covered_statements = 0
        self.grand_total_statements = 0
        self.grand_total_max_mcdc_covered_branches = 0
        self.grand_total_mcdc_branches = 0
        self.grand_total_max_covered_mcdc_pairs = 0
        self.grand_total_mcdc_pairs = 0
        self.grand_total_max_covered_function_calls = 0
        self.grand_total_function_calls = 0
        self.grand_total_max_covered_functions = 0
        self.grand_total_max_coverable_functions = 0
        self.grand_total_total_basis_path = 0
        self.grand_total_cov_basis_path = 0
        for srcFile in self.units:

            if not self.hasAnyCov(srcFile):
                continue
                
            try:
                hasFunCov = self.hasFunctionCoverage(srcFile.coverage_types)
            except:
                hasFunCov = self.hasFunctionCoverage([srcFile.coverage_type])
                                    
            try:
                if srcFile.coverage_type in (COVERAGE_TYPE_TYPE_T.FUNCTION_FUNCTION_CALL, COVERAGE_TYPE_TYPE_T.FUNCTION_COVERAGE):
                    self.has_function_coverage = True
            except Exception as e:
                self.has_function_coverage = self.api.environment.get_option("VCAST_DISPLAY_FUNCTION_COVERAGE")
            
            # 2019 SP1 and above until Sam changes it again :P
            try:
                if hasFunCov:
                    self.has_call_coverage = True
            except:
                if srcFile.has_call_coverage:
                    self.has_call_coverage = True
            
            try:
                metrics = srcFile.metrics
            except:
                metrics = srcFile.cover_metrics
                
            try:
                cov_type = srcFile.coverage_types
            except:
                cov_type = srcFile.coverage_type
                            
            entry = {}
            entry["unit"] = srcFile
            entry["functions"] = []
            entry["complexity"] = 0
            entry["coverage"] = self.add_coverage(True, srcFile, metrics, cov_type)
            functions_added = False
            funcs_with_cover_data = []
            for func in srcFile.functions:
                try:
                    hasAnyCov = func.has_coverage_data
                except:
                    hasAnyCov =  func.instrumented_functions[0].has_coverage_data
                    
                if hasAnyCov:
                    functions_added = True
                    funcs_with_cover_data.append(func)
                    
            if self.using_cover:
                sorted_funcs = sorted(funcs_with_cover_data,key=attrgetter('cover_data.index'))
            else:
                try:
                    sorted_funcs = sorted(funcs_with_cover_data,key=attrgetter('cover_data.id'))
                except:
                    sorted_funcs = sorted(funcs_with_cover_data,key=attrgetter('instrumented_functions.index'))

            for func in sorted_funcs:
                try:
                    cover_function = func.cover_data.metrics
                except:
                    cover_function = func.metrics
                
                functions_added = True
                try:
                    complexity = func.complexity
                except:
                    complexity = func.metrics.complexity
                    
                if complexity >= 0:
                    entry["complexity"] += complexity
                    self.grand_total_complexity += complexity
                func_entry = {}
                func_entry["func"] = func
                func_entry["complexity"] = complexity
                func_entry["coverage"] = self.add_coverage(False, func, cover_function, cov_type)
                self.num_functions += 1
                entry["functions"].append(func_entry)
            if functions_added:
                self.our_units.append(entry)

            self.grand_total_max_covered_branches += metrics.max_covered_branches
            self.grand_total_branches += metrics.branches
            self.grand_total_max_covered_statements += metrics.max_covered_statements
            self.grand_total_statements += metrics.statements
            self.grand_total_max_mcdc_covered_branches += metrics.max_covered_mcdc_branches
            self.grand_total_mcdc_branches += metrics.mcdc_branches
            self.grand_total_max_covered_mcdc_pairs += metrics.max_covered_mcdc_pairs
            self.grand_total_mcdc_pairs += metrics.mcdc_pairs
            self.grand_total_max_covered_function_calls += metrics.max_covered_function_calls
            self.grand_total_function_calls += metrics.function_calls
            #(total_funcs, funcs_covered) = cover_file.functions_covered
            #self.grand_total_max_covered_functions += funcs_covered
            #self.grand_total_max_coverable_functions += total_funcs

            if "BASIS_PATH" in str(cov_type):
                (cov, total) = srcFile.basis_paths_coverage
                self.grand_total_total_basis_path += total
                self.grand_total_cov_basis_path += cov

        self.coverage = self.grand_total_coverage(cov_type)
        self.num_units = len(self.our_units)

#
# BaseGenerateXml - Generate the XML Modified 'Emma' coverage data
#
    def generate_cover(self):
        self.units = []
        if self.using_cover:
            self.units = self.api.File.all()
            self.units.sort(key=lambda x: (x.coverage_type, x.unit_index))
        else:
            self.units = self.api.Unit.all()
            
        # unbuilt (re: Error) Ada environments causing a crash
        try:
            cov_type = self.api.environment.coverage_type_text
        except Exception as e:
            parse_traceback.parse(traceback.format_exc(), self.print_exc, self.compiler,  self.testsuite,  self.env,  self.build_dir)
            return
            
        self._generate_cover(cov_type)

        self.start_cov_file_environment()
        self.write_cov_units()
        self.end_cov_file_environment()

#
# BaseGenerateXml - write the start of the coverage file for and environment
#
    def start_cov_file_environment(self):
        self.start_cov_file()
        self.fh_data += ('  <stats>\n')
        self.fh_data += ('    <environments value="1"/>\n')
        self.fh_data += ('    <units value="%d"/>\n' % self.num_units)
        self.fh_data += ('    <subprograms value="%d"/>\n' % self.num_functions)
        self.fh_data += ('  </stats>\n')
        self.fh_data += ('  <data>\n')
        
        self.fh_data += ('    <all name="all environments">\n')
        if self.coverage["statement"]:
            self.fh_data += ('      <coverage type="statement, %%" value="%s"/>\n' % self.coverage["statement"])
        if self.coverage["branch"]:
            self.fh_data += ('      <coverage type="branch, %%" value="%s"/>\n' % self.coverage["branch"])
        if self.coverage["mcdc"]:
            self.fh_data += ('      <coverage type="mcdc, %%" value="%s"/>\n' % self.coverage["mcdc"])
        if self.coverage["basispath"]:
            self.fh_data += ('      <coverage type="basispath, %%" value="%s"/>\n' % self.coverage["basispath"])
        if self.coverage["function"]:
            self.fh_data += ('      <coverage type="function, %%" value="%s"/>\n' % self.coverage["function"])
        if self.coverage["functioncall"]:
            self.fh_data += ('      <coverage type="functioncall, %%" value="%s"/>\n' % self.coverage["functioncall"])
        self.fh_data += ('      <coverage type="complexity, %%" value="0%% (%s / 0)"/>\n' % self.grand_total_complexity)
        self.fh_data += ('\n')
        
        if isinstance(self, GenerateManageXml):
            self.fh_data += ('      <environment name="%s">\n' % escape(self.manageProjectName, quote=False))
        else:
            self.fh_data += ('      <environment name="%s">\n' % escape(self.jenkins_name, quote=False))
        if self.coverage["statement"]:
            self.fh_data += ('        <coverage type="statement, %%" value="%s"/>\n' % self.coverage["statement"])
        if self.coverage["branch"]:
            self.fh_data += ('        <coverage type="branch, %%" value="%s"/>\n' % self.coverage["branch"])
        if self.coverage["mcdc"]:
            self.fh_data += ('        <coverage type="mcdc, %%" value="%s"/>\n' % self.coverage["mcdc"])
        if self.coverage["basispath"]:
            self.fh_data += ('        <coverage type="basispath, %%" value="%s"/>\n' % self.coverage["basispath"])
        if self.coverage["function"]:
            self.fh_data += ('        <coverage type="function, %%" value="%s"/>\n' % self.coverage["function"])
        if self.coverage["functioncall"]:
            self.fh_data += ('        <coverage type="functioncall, %%" value="%s"/>\n' % self.coverage["functioncall"])
        self.fh_data += ('        <coverage type="complexity, %%" value="0%% (%s / 0)"/>\n' % self.grand_total_complexity)
        self.fh_data += ('\n')

##########################################################################
# This class generates the XML (JUnit based) report for the overall
# (Emma based) report for Coverage
#
class GenerateManageXml (BaseGenerateXml):

# GenerateManageXml

    def __init__(self, FullManageProjectName, verbose = False, 
                       cbtDict = None, 
                       generate_exec_rpt_each_testcase = True,
                       skipReportsForSkippedEnvs = False,
                       report_failed_only = False,
                       no_full_reports = False,
                       print_exc = False):
                       
        super(GenerateManageXml, self).__init__(FullManageProjectName, verbose)
        self.using_cover = False
        self.api = VCProjectApi(FullManageProjectName)
        self.has_sfp_enabled = self.api.environment.get_option("VCAST_COVERAGE_SOURCE_FILE_PERSPECTIVE")        

        self.FullManageProjectName = FullManageProjectName        
        self.generate_exec_rpt_each_testcase = generate_exec_rpt_each_testcase
        self.skipReportsForSkippedEnvs = skipReportsForSkippedEnvs
        self.report_failed_only = report_failed_only
        self.cbtDict = cbtDict
        self.no_full_reports = no_full_reports
        self.failed_count = 0
        self.passed_count = 0
        self.print_exc = print_exc

        self.cleanupXmlDataDir()

    def cleanupXmlDataDir(self):
        path="xml_data"
        import glob
        # if the path exists, try to delete all file in it
        if os.path.isdir(path):
            for file in glob.glob(path + "/*.*"):
                try:
                    os.remove(file);
                except:
                    teePrint.teePrint("   *INFO: File System Error removing file after failed to remove directory: " + path + "/" + file + ".  Check console for environment build/execution errors")
                    if print_exc:  traceback.print_exc()

        # we should either have an empty directory or no directory
        else:
            try:
                os.mkdir(path)
            except:
                print("failed making path: " + path)
                teePrint.teePrint("   *INFO: File System Error creating directory: " + path + ".  Check console for environment build/execution errors")
                if print_exc:  traceback.print_exc()
                
    def __del__(self):
        self.api.close()

# GenerateManageXml

    def generate_cover(self):
        if isinstance(self.api, CoverApi):
            self.using_cover = True
        else:
            self.using_cover = False
        self.units = self.api.project.cover_api.SourceFile.all() ##self.api.project.cover_api.File.all()
        self._generate_cover(None)
        self.start_cov_file_environment()
        self.write_cov_units()
        self.end_cov_file_environment()

    def fixupReport(self, report_name):

        fixup = False
        if self.api.tool_version.startswith("19 "):
            fixup = True
        elif self.api.tool_version.startswith("19sp1"):
            fixup = True
            # custom report patch for SP1 problem - should be fixed in future release      
            old_init = CustomReport._post_init
            def new_init(self):
                old_init(self)
                self.context['report']['use_all_testcases'] = True
            CustomReport._post_init = new_init

        if not fixup:
            return
            
        with open(report_name,"r") as fd:
            data = fd.read() 

        #fix up inline CSS because of Content Security Policy violation
        newData = data[: data.index("<style>")-1] +  """
        <link rel="stylesheet" href="vector_style.css">
        """ + data[data.index("</style>")+8:]
        
        #fix up style directive because of Content Security Policy violation
        newData = newData.replace("<div class='event bs-callout' style=\"position: relative\">","<div class='event bs-callout relative'>")
        
        #fixup the inline VectorCAST image because of Content Security Policy violation
        regex_str = r"<img alt=\"Vector\".*"
        newData =  re.sub(regex_str,"<img alt=\"Vector\" src=\"vectorcast.png\"/>",newData)
        
        with open(report_name, "w") as fd:
            fd.write(newData)
       
        vc_scripts = os.path.join(os.getenv("WORKSPACE"),"vc_scripts")
        
        shutil.copy(os.path.join(vc_scripts,"vector_style.css"), "management/vector_style.css")
        shutil.copy(os.path.join(vc_scripts,"vectorcast.png"), "management/vectorcast.png")
        
    def generate_local_results(self, results, key):
        # get the level from the name

        if len(key.split("/")) != 3:
            comp, ts, group, env_name = key.split("/")
        else:
            comp, ts, env_name = key.split("/")
            
        env_key = comp + "/" + ts + "/" + env_name
        
        env = self.api.project.environments[env_key]
        env_def = self.api.project.environments[env_key].definition
    
        build_dir = os.path.join(self.api.project.workspace,env.relative_working_directory)
        vceFile =  os.path.join(build_dir, env.name+".vce")
        
        xmlUnitReportName = os.getcwd() + os.sep + "xml_data" + os.sep + "test_results_" + key.replace("/","_") + ".xml"

        localXML = GenerateXml(self.FullManageProjectName, build_dir, env_name, comp, ts, 
                               None, key, xmlUnitReportName, None, None, False, 
                               self.cbtDict, 
                               self.generate_exec_rpt_each_testcase, 
                               self.skipReportsForSkippedEnvs, 
                               self.report_failed_only,
                               self.print_exc)
                               
        localXML.topLevelAPI = self.api
        localXML.generate_unit()
        
        ##need_fixup
        if not self.no_full_reports:
            report_name = os.path.join("management", comp + "_" + ts + "_" + env_name + ".html")
            if isinstance(localXML.api, CoverApi):
                CustomReport.report_from_api(localXML.api, report_type="Demo", formats=["HTML"], output_file=report_name, sections=["CUSTOM_HEADER", "REPORT_TITLE", "TABLE_OF_CONTENTS", "CONFIG_DATA", "METRICS", "MCDC_TABLES",  "AGGREGATE_COVERAGE", "CUSTOM_FOOTER"])
            else:
                localXML.api.report(report_type="FULL_REPORT", formats=["HTML"], output_file=report_name)
            self.fixupReport(report_name)

        
# GenerateManageXml
    def generate_testresults(self):
        testcaseString = """
        <testcase name="%s" classname="%s" time="0">
            %s
        </testcase>
"""                    
        results = self.api.project.repository.get_full_status([])
        all_envs = []
        for env in self.api.Environment.all():
            all_envs.append(env.level._full_path)
            
        if results['ALL']['testcase_results'] == {}:
            return
            
        total   = results['ALL']['testcase_results']['total_count']
        success = results['ALL']['testcase_results']['success_count']
        errors  = total - success
        failed  = errors
        self.localDataOnly = True
        self.fh_data = ""            
        self.fh_data += ("<?xml version=\"1.0\" encoding=\"" + self.encFmt + "\"?>\n")
        self.fh_data += ("<testsuites>\n")
        self.fh_data += ("    <testsuite errors=\"%d\" tests=\"%d\" failures=\"%d\" name=\"%s\" id=\"1\">\n" %
            (errors,total,failed,escape(self.manageProjectName, quote=False)))
            
        for result in results:
            if result in all_envs:
                if len(result.split("/")) != 3:
                    comp, ts, group, env_name = result.split("/")
                else:
                    comp, ts, env_name = result.split("/")
                if results[result]['local'] != {}:
                    self.generate_local_results(results,result)                    
                else:
                    for key in results[result]['imported'].keys():
                        self.localDataOnly = False
                        importedResult = results[result]['imported'][key]
                        total   = importedResult['testcase_results']['total_count']
                        success = importedResult['testcase_results']['success_count']
                        errors  = total - success
                        failed  = errors
                        importName = importedResult['name']
                        classname = "ImportedResults." + importName + "." + comp + "." + ts + "." + env_name
                        classname = comp + "." + ts + "." + env_name
                        for idx in range(1,success+1):
                            tc_name_full = "ImportedResults." + importName + ".TestCase.PASS.%03d" % idx
                            extraStatus = "\n            <skipped/>\n"
                            self.fh_data += (testcaseString % (tc_name_full, classname, extraStatus))
                            self.passed_count += 1

                        for idx in range(1,failed+1):
                            tc_name_full = "ImportedResults." + importName + ".TestCase.FAIL.%03d" % idx
                            extraStatus = "\n            <failure type=\"failure\"/>\n"
                            self.fh_data += (testcaseString % (tc_name_full, classname, extraStatus))
                            self.failed_count += 1
            
        self.fh_data += ("   </testsuite>\n")
        self.fh_data += ("</testsuites>\n")
        if not self.localDataOnly:
            with open(self.unit_report_name, "w") as fd:
                try:
                    fd.write(self.fh_data)
                except:
                    fd.write(unicode(self.fh_data))
        
##########################################################################
# This class generates the XML (Junit based) report for dynamic tests and
# the XML (Emma based) report for Coverage results
#
# In both cases these are for a single environment
#
class GenerateXml(BaseGenerateXml):

    def __init__(self, FullManageProjectName, build_dir, env, compiler, testsuite, cover_report_name, jenkins_name, unit_report_name, jenkins_link, jobNameDotted, verbose = False, cbtDict= None, generate_exec_rpt_each_testcase = True, skipReportsForSkippedEnvs = False, report_failed_only = False, print_exc = False):
        super(GenerateXml, self).__init__(FullManageProjectName, verbose)

        self.cbtDict = cbtDict
        self.FullManageProjectName = FullManageProjectName
        self.generate_exec_rpt_each_testcase = generate_exec_rpt_each_testcase
        self.skipReportsForSkippedEnvs = skipReportsForSkippedEnvs
        self.report_failed_only = report_failed_only
        self.print_exc = print_exc
        self.topLevelAPI = None
        
        ## use hash code instead of final directory name as regression scripts can have overlapping final directory names
        
        build_dir_4hash = build_dir.upper()
        build_dir_4hash = "/".join(build_dir_4hash.split("/")[-2:])
        
        # Unicode-objects must be encoded before hashing in Python 3
        if sys.version_info[0] >= 3:
            build_dir_4hash = build_dir_4hash.encode(self.encFmt)

        self.hashCode = hashlib.md5(build_dir_4hash).hexdigest()
        
        if verbose:
            print ("gen Dir: " + str(build_dir_4hash)+ " Hash: " +self.hashCode)

        #self.hashCode = build_dir.split("/")[-1].upper()
        self.build_dir = build_dir
        self.env = env
        self.compiler = compiler
        self.testsuite = testsuite
        self.cover_report_name = cover_report_name
        self.jenkins_name = jenkins_name
        self.unit_report_name = unit_report_name
        self.jenkins_link = jenkins_link
        self.jobNameDotted = jobNameDotted
        self.using_cover = False
        cov_path = os.path.join(build_dir,env + '.vcp')
        unit_path = os.path.join(build_dir,env + '.vce')
        if os.path.exists(cov_path):
            self.using_cover = True
            self.api = CoverApi(cov_path)
        elif os.path.exists(unit_path):
            self.using_cover = False
            self.api = UnitTestApi(unit_path)
        else:
            self.api = None
            if verbose:
                print("Error: Could not determine project type for {}/{}".format(build_dir, env))
                print("       {}/{}/{}".format(compiler, testsuite, env))
            return

        self.api.commit = dummy
        self.failed_count = 0
        self.passed_count = 0

#
# GenerateXml - add any compound tests to the unit report
#
    def add_compound_tests(self):
        for tc in self.api.TestCase.all():
            if tc.kind == TestCase.KINDS['compound']:
                if not tc.for_compound_only:
                    self.write_testcase(tc, "<<COMPOUND>>", "<<COMPOUND>>")

#
# GenerateXml - add any intialisation tests to the unit report
#
    def add_init_tests(self):
        for tc in self.api.TestCase.all():
            if tc.kind == TestCase.KINDS['init']:
                if not tc.for_compound_only:
                    self.write_testcase(tc, "<<INIT>>", "<<INIT>>")

#
# GenerateXml - Find the test case file
#
    def generate_unit(self):
        
        if isinstance(self.api, CoverApi):
            try:
                self.start_system_test_file()

                if self.topLevelAPI == None:
                    api = VCProjectApi(self.FullManageProjectName)
                else:
                    api = self.topLevelAPI
                        
                for env in api.Environment.all():
                    if env.compiler.name == self.compiler and env.testsuite.name == self.testsuite and env.name == self.env and env.system_tests:
                        for st in env.system_tests:
                            pass_fail_rerun = ""
                            if st.run_needed and st.type == 2: #SystemTestType.MANUAL:
                                pass_fail_rerun =  ": Manual system tests can't be run in Jenkins"
                            elif st.run_needed:
                                pass_fail_rerun =  ": Needs to be executed"
                            elif st.passed:
                                pass_fail_rerun =  ": Passed"
                            else:
                                pass_fail_rerun =  ": Failed"
                                
                            level = env.compiler.name + "/" + env.testsuite.name + "/" + env.name
                            if self.verbose:
                                print (level, st.name, pass_fail_rerun)
                            self.write_testcase(st, level, st.name, env.definition.is_monitored)
                from generate_qa_results_xml import saveQATestStatus
                saveQATestStatus(self.FullManageProjectName)
                
                if self.topLevelAPI == None:
                    api.close()

            except ImportError as e:
                from generate_qa_results_xml import genQATestResults
                pc,fc = genQATestResults(self.FullManageProjectName, self.compiler+ "/" + self.testsuite, self.env, True, self.encFmt)
                self.failed_count += fc
                self.passed_count += pc
                return

        else:
            try:
                self.start_unit_test_file()
                self.add_compound_tests()
                self.add_init_tests()
                for unit in self.api.Unit.all():
                    if unit.is_uut:
                        for func in unit.functions:
                            if not func.is_non_testable_stub:
                                for tc in func.testcases:
                                    try:
                                        vctMap = tc.is_vct_map
                                    except:
                                        vctMap = False
                                    if not tc.is_csv_map and not vctMap:
                                        if not tc.for_compound_only or tc.testcase_status == "TCR_STRICT_IMPORT_FAILED":
                                            self.write_testcase(tc, tc.function.unit.name, tc.function.display_name)

            except AttributeError as e:
                parse_traceback.parse(traceback.format_exc(), self.verbose, self.compiler,  self.testsuite,  self.env,  self.build_dir)
                
        self.end_test_results_file()
#
# GenerateXml - write the end of the jUnit XML file and close it
#
    def end_test_results_file(self):
        self.fh_data += ("   </testsuite>\n")
        self.fh_data += ("</testsuites>\n")
        with open(self.unit_report_name, "w") as fd:
            fd.write(self.fh_data)

#
# GenerateXml - start the JUnit XML file
#

    def start_system_test_file(self):
        if self.verbose:
            print("  Writing testcase xml file:        {}".format(self.unit_report_name))

        errors = 0
        failed = 0
        success = 0                                            
        
        from vector.apps.DataAPI.vcproject_api import VCProjectApi 
        
        if self.topLevelAPI == None:
            api = VCProjectApi(self.FullManageProjectName)
        else:
            api = self.topLevelAPI
        
        for env in api.Environment.all():
            if env.compiler.name == self.compiler and env.testsuite.name == self.testsuite and env.name == self.env and env.system_tests:
                for st in env.system_tests:
                    if st.passed == st.total:
                        success += 1
                        self.passed_count += 1
                    else:
                        failed += 1
                        errors += 1  
                        self.failed_count += 1
                        
        if self.topLevelAPI == None:
            api.close()            

        self.fh_data = ""        
        self.fh_data += ("<?xml version=\"1.0\" encoding=\"" + self.encFmt + "\"?>\n")
        self.fh_data += ("<testsuites>\n")
        self.fh_data += ("    <testsuite errors=\"%d\" tests=\"%d\" failures=\"%d\" name=\"%s\" id=\"1\">\n" %
            (errors,success+failed+errors, failed, escape(self.env, quote=False)))
                
    def start_unit_test_file(self):
        if self.verbose:
            print("  Writing testcase xml file:        {}".format(self.unit_report_name))

        errors = 0
        failed = 0
        success = 0                                            
        
        for tc in self.api.TestCase.all():
            try:
                vctMap = tc.is_vct_map
            except:
                vctMap = False
        
            if (not tc.for_compound_only or tc.testcase_status == "TCR_STRICT_IMPORT_FAILED") and not tc.is_csv_map and not vctMap:
                if not tc.passed:
                    self.failed_count += 1
                    failed += 1
                    if tc.execution_status != "EXEC_SUCCESS_FAIL ":
                        errors += 1
                else:
                    success += 1
                    self.passed_count += 1
        self.fh_data = ""            
        self.fh_data += ("<?xml version=\"1.0\" encoding=\"" + self.encFmt + "\"?>\n")
        self.fh_data += ("<testsuites>\n")
        self.fh_data += ("    <testsuite errors=\"%d\" tests=\"%d\" failures=\"%d\" name=\"%s\" id=\"1\">\n" %
            (errors,success+failed+errors, failed, escape(self.env, quote=False)))

    def testcase_failed(self, tc):
        
        try:
            from vector.apps.DataAPI.manage_models import SystemTest
            if (isinstance(tc, SystemTest)):
                if tc.run_needed and tc.type == 2: 
                    return False
                elif tc.run_needed:
                    return False
                elif tc.passed == tc.total:
                    return False
                else:
                    return True
        except:
            pass
            
        if not tc.passed:
            return True
            
        return False

#
# GenerateXml - write a testcase to the jUnit XML file
#
    def write_testcase(self, tc, unit_name, func_name, st_is_monitored = False):
    
        failure_message = ""
        
        if self.report_failed_only and not self.testcase_failed(tc):
            return

        isSystemTest = False
        
        try:
            from vector.apps.DataAPI.manage_models import SystemTest
            if (isinstance(tc, SystemTest)):
                isSystemTest = True
        except:
            pass

        start_tdo = datetime.now()
        end_tdo   = None
        
        # don't do CBT analysis on migrated cover environments
        if isSystemTest and not st_is_monitored:
            tcSkipped = False 
            
        # If cbtDict is None, no build log was passed in...don't mark anything as skipped 
        elif self.skipReportsForSkippedEnvs or self.cbtDict == None:
            tcSkipped = False 
            
        # else there is something check , if the length of cbtDict is greater than zero
        elif len(self.cbtDict) > 0:
            tcSkipped, start_tdo, end_tdo = self.was_test_case_skipped(tc,"/".join([unit_name, func_name, tc.name]),isSystemTest)
            
        # finally - there was something to check, but it was empty
        else:
            tcSkipped = True
         
        if end_tdo:
            deltaTimeStr = str((end_tdo - start_tdo).total_seconds())
        else:
            deltaTimeStr = "0.0"

        unit_name = escape(unit_name, quote=False)
        func_name = escape(func_name, quote=True)
        tc_name = escape(tc.name, quote=False)
        compiler = escape(self.compiler, quote=False).replace(".","")
        testsuite = escape(self.testsuite, quote=False).replace(".","")
        envName = escape(self.env, quote=False).replace(".","")
        
        tc_name_full =  unit_name + "." + func_name + "." + tc_name

        classname = compiler + "." + testsuite + "." + envName

        if isSystemTest:        
            exp_total = tc.total
            exp_pass = tc.passed
            result = "  System Test Build Status: " + tc.build_status + ". \n   System Test: " + tc.name + " \n   Execution Status: "
            if tc.run_needed and tc.type == 2: #SystemTestType.MANUAL:
                result += "Manual system tests can't be run in Jenkins"
                tc.passed = 1
            elif tc.run_needed:
                result += "Needs to be executed"
                tc.passed = 1
            elif tc.passed == tc.total:
                result += "Passed"
            else:
                result += "Failed {} / {} ".format(tc.passed, tc.total)
                tc.passed = 0
                
        else:
            summary = tc.history.summary
            exp_total = summary.expected_total
            exp_pass = exp_total - summary.expected_fail
            if self.api.environment.get_option("VCAST_OLD_STYLE_MANAGEMENT_REPORT"):
                exp_pass += summary.control_flow_total - summary.control_flow_fail
                exp_total += summary.control_flow_total + summary.signals + summary.unexpected_exceptions

            result = self.__get_testcase_execution_results(
                tc,
                classname,
                tc_name_full)
            
            if tc.testcase_status == "TCR_STRICT_IMPORT_FAILED":
                result += "\nStrict Test Import Failure.".encode()
    
            # Failure takes priority  
            if tc.status != "TC_EXECUTION_NONE":
                failure_message = self.convertExecStatus(tc.execution_status)
            else:
                failure_message = "Test Not Executed"

        status = ""
        if tc.passed == None:
            extraStatus = "\n            <skipped/>\n"

        elif not tc.passed:
            if tcSkipped: 
                status = "Testcase may have been skipped by VectorCAST Change Based Testing.  Last execution data shown.\n\nFAIL"
            else:
                status = "FAIL"
            extraStatus = "\n            <failure type=\"failure\" message=\"" + failure_message + "\"/>\n"
            
            msg = "{} {} / {}  \n\nExecution Report:\n {}".format(status, exp_pass, exp_total, result)
        elif tcSkipped:
            extraStatus = "\n            <skipped/>\n"
        else:
            status = "PASS"
            extraStatus = ""

        if status != "":
            msg = "{} {} / {}  \n\nExecution Report:\n {}".format(status, exp_pass, exp_total, result)        
            msg = escape(msg, quote=False)
            msg = msg.replace("\"","")
            msg = msg.replace("\n","&#xA;")
        
        testcaseStringExtraStatus="""
        <testcase name="%s" classname="%s" time="%s">
            %s
            <system-out>
%s                     
            </system-out>
        </testcase>
"""        
        testcaseString ="""
        <testcase name="%s" classname="%s" time="%s">
            %s
        </testcase>
"""
        if status != "":
            testcaseString = testcaseStringExtraStatus
            self.fh_data += (testcaseString % (tc_name_full, classname, deltaTimeStr, extraStatus, msg))
        else:
            self.fh_data += (testcaseString % (tc_name_full, classname, deltaTimeStr, extraStatus))

## GenerateXml

    def was_test_case_skipped(self, tc, searchName, isSystemTest):
        import sys, pprint
        try:
            if isSystemTest:
                compoundTests, initTests,  simpleTestcases = self.cbtDict[self.hashCode]
                # use tc.name because system tests aren't for a specific unit/function
                if tc.name in simpleTestcases.keys():
                    return [False, simpleTestcases[tc.name][0], simpleTestcases[tc.name][1]]
                else:
                    self.__print_test_case_was_skipped(searchName, tc.passed)
                    return [True, None, None]
            else:
                #Failed import TCs don't get any indication in the build.log
                if tc.testcase_status == "TCR_STRICT_IMPORT_FAILED":
                    return [False, None, None]
                    
                compoundTests, initTests,  simpleTestcases = self.cbtDict[self.hashCode]
                                
                #Recursive Compound don't get any named indication in the build.log
                if tc.kind == TestCase.KINDS['compound'] and (tc.testcase_status == "TCR_RECURSIVE_COMPOUND" or searchName in compoundTests.keys()):
                    return [False, compoundTests[searchName][0], compoundTests[searchName][1]]
                elif tc.kind == TestCase.KINDS['init'] and searchName in initTests.keys():
                    return [False, initTests[searchName][0], initTests[searchName][1]]
                elif searchName in simpleTestcases.keys() or tc.testcase_status == "TCR_NO_EXPECTED_VALUES":
                    #print ("found" , self.hashCode, searchName, str( simpleTestcases[searchName][1] - simpleTestcases[searchName][0]))
                    return [False, simpleTestcases[searchName][0], simpleTestcases[searchName][1]]
                else:
                    self.__print_test_case_was_skipped(searchName, tc.passed)
                    return [True, None, None]
        except KeyError:
            self.__print_test_case_was_skipped(tc.name, tc.passed)
            return [True, None, None]
        except Exception as e: 
            parse_traceback.parse(traceback.format_exc(), self.print_exc, self.compiler,  self.testsuite,  self.env,  self.build_dir)
            if self.print_exc:
                pprint.pprint ("CBT Dictionary: \n" + self.cbtDict, width = 132)

## GenerateXml

    def __get_testcase_execution_results(self, tc, classname, tc_name):
    
        if not self.generate_exec_rpt_each_testcase:
            return "Execution Report disabled by using --dont-generate-individual-reports"
            
        report_name_hash =  '.'.join(
            ["execution_results", classname, tc_name])
        # Unicode-objects must be encoded before hashing in Python 3
        if sys.version_info[0] >= 3:
            report_name_hash = report_name_hash.encode(self.encFmt)

        report_name = hashlib.md5(report_name_hash).hexdigest()

        import time

        try:
            self.api.report(
                testcases=[tc],
                single_testcase=True,
                report_type="Demo",
                formats=["TEXT"],
                output_file=report_name,
                sections=[ "TESTCASE_SECTIONS"],
                testcase_sections=["EXECUTION_RESULTS"])
                
            with open(report_name,"rb") as fd:
                out = fd.read()
                
            out = out.decode('utf-8').encode(self.encFmt)
            
            os.remove(report_name)
        except:
            out = "No execution results found"
            parse_traceback.parse(traceback.format_exc(), self.print_exc, self.compiler,  self.testsuite,  self.env,  self.build_dir)

        #out = bytes(out, 'utf-8').decode('utf-8', 'ignore')

        return out

## GenerateXml

    def __print_test_case_was_skipped(self, searchName, passed):
        if self.verbose:
            print("skipping ", self.hashCode, searchName, passed)

def __generate_xml(xml_file, envPath, env, xmlCoverReportName, xmlTestingReportName, teePrint):
    if xml_file.api == None:
        teePrint.teePrint ("\nCannot find project file (.vcp or .vce): " + envPath + os.sep + env)
        
    elif xml_file.using_cover:
        xml_file.generate_cover()
        teePrint.teePrint ("\nvectorcast-coverage plugin for Jenkins compatible file generated: " + xmlCoverReportName)

    else:
        xml_file.generate_unit()
        teePrint.teePrint ("\nJunit plugin for Jenkins compatible file generated: " + xmlTestingReportName)

if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('environment', help='VectorCAST environment name')
    parser.add_argument('-v', '--verbose', default=False, help='Enable verbose output', action="store_true")
    args = parser.parse_args()
    
    envPath = os.path.dirname(os.path.abspath(args.environment))
    env = os.path.basename(args.environment)
    
    if env.endswith(".vcp"):
        env = env[:-4]
        
    if env.endswith(".vce"):
        env = env[:-4]
        
    jobNameDotted = env
    jenkins_name = env
    jenkins_link = env
    xmlCoverReportName = "coverage_results_" + env + ".xml"
    xmlTestingReportName = "test_results_" + env + ".xml"

    xml_file = GenerateXml(env,
                           envPath,
                           env, "", "", 
                           xmlCoverReportName,
                           jenkins_name,
                           xmlTestingReportName,
                           jenkins_link,
                           jobNameDotted, 
                           args.verbose, 
                           None)

    with tee_print.TeePrint() as teePrint:
        __generate_xml(
            xml_file,
            envPath,
            env,
            xmlCoverReportName,
            xmlTestingReportName,
            teePrint)
