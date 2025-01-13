import tree_sitter_c as tsc
import tree_sitter_matlab as tsm
import tree_sitter_python as tsp
import tree_sitter_java as tsj
from tree_sitter import Language, Parser
import tree_sitter
from pprint import pp
import sys
import os
import array
import json
import mariadb

C_LANGUAGE = Language(tsc.language())
MATLAB_LANGUAGE = Language(tsm.language())
PYTHON_LANGUAGE = Language(tsp.language())
JAVA_LANGUAGE = Language(tsj.language())
CURRENT_LANGUAGE = MATLAB_LANGUAGE


SQL_USER = "root"
SQL_PASSWORD = "agOdnek2"

def contains(self, s):
    return (s.start_point[0] > self.start_point[0] or\
            (s.start_point[0] == self.start_point[0] and\
             s.start_point[1] >= self.start_point[1])) and\
           (s.end_point[0] < self.end_point[0] or\
            (s.end_point[0] == self.end_point[0] and\
             s.end_point[1] <= self.end_point[1]))

tree_sitter.Node.contains = contains


def test(pattern_conn, test_id):
    cur = pattern_conn.cursor()

    cur.execute(
        "SELECT text, result, pattern_id FROM pattern_test WHERE id=?",
        (test_id,)
    )

    (test_text, correct_result, pattern_id) = cur.fetchone()

    # Assume new field code_string (nullable longtext)
    # update regex_string to longtext
    cur.execute(
        "SELECT regex_string, language, code_string FROM pattern WHERE id=?",
        (pattern_id,)
    )

    (ast_search, language, code_match) = cur.fetchone()

    if language.lower() == "python":
        CURRENT_LANGUAGE = PYTHON_LANGUAGE
    elif language.lower() == "matlab":
        CURRENT_LANGUAGE = MATLAB_LANGUAGE
    elif language.lower() == "c":
        CURRENT_LANGUAGE = C_LANGUAGE
    elif language.lower() == "java":
        CURRENT_LANGUAGE = JAVA_LANGUAGE
    else:
        print("Unsupported language!")
        return -1


    parser = Parser(CURRENT_LANGUAGE)

    tree = parser.parse(test_text, encoding='utf8')
    query = CURRENT_LANGUAGE.query(ast_search)
    matches = query.matches(tree.root_node)
    matched = False

    if len(matches) > 0:
        if code_match is not None:
            # Create an arg list
            args = query_code[query_code.index('(') + 1:query_code.index(')')]
            args = [s.strip() for s in args.split(',')]
            args = args[1:]

            exec(query_code)

            for match in matches:
                func_call = 'antipattern(tree, '
                            
                for i, arg in enumerate(args):
                    func_call += "match[1]['" + args[i] + "']"
                    if i < len(args) - 1:
                        func_call += ', '
                func_call += ')'
                eval_result = eval(func_call)

                if isinstance(eval_result, bool):
                    if eval_result:
                        matched = True
                else:
                    if eval_result[0]:
                        matched = True
        else:
            matched = True

    passed = (matched and correct_result == 1)

    cur.execute(
        "UPDATE pattern_test SET pass=? WHERE id=?",
        (passed,test_id,)
    )
    pattern_conn.commit()

    if matched:
        print(1)
    else
        print(0)

    return 0

def grade(pattern_conn, submission_id):

    # Connect to the webta database

    try:
        assignment_conn = mariadb.connect(
            user=SQL_USER,
            password=SQL_PASSWORD,
            host="localhost",
            port=3306,
            database="engta"
        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        return -1

    # Create the initial critique info
    main_critique = {}
    main_critique["version"] = 7
    main_critique["num_critical"] = 0
    main_critique["overall_status"] = ""
    main_critique["num_pass"] = 0
    main_critique["num_warning"] = 0
    main_critique["can_process_file"] = True
    main_critique["executive_summary"] = ""


    # Create our cursor
    assignment_cur = assignment_conn.cursor()

    # Make sure the assignment exists
    assignment_cur.execute(
        "SELECT id FROM submission WHERE id=?",
        (submission_id,)
    )

    submission = assignment_cur.fetchone()

    if submission is None:
        print("That submission does not exist")
        return -1

    # Create the initial entry for the critique
    assignment_cur.execute(
        "INSERT INTO critique (version, num_critical, date_created, overall_status, last_updated, num_pass, " +\
        "submission_id, num_warning, can_process_file, executive_summary) values (" +\
        "?, 0, NOW(), '', NOW(), 0, ?, 0, 1, '');",
        (main_critique["version"],submission_id,)
    )
    assignment_conn.commit()

    # Get the id of the entry
    main_critique["id"] = assignment_conn.insert_id()

    # Get all files they submitted
    assignment_cur.execute(
        "SELECT id, version, CONVERT(file_data USING utf8) as file_data, filetype, " +\
        "filesize, filename FROM submission_file WHERE submissionid=? and can_process_file=1",
        (submission_id,)
    )

    submitted_files = assignment_cur.fetchall()
    
    pattern_cur = pattern_conn.cursor()

    critiques = []

    for (file_id, file_version, file_data, file_type, file_size, file_name) in submitted_files:
        
        # Get the language we should use.
        if file_name.endswith(".py"):
            CURRENT_LANGUAGE = PYTHON_LANGUAGE
            language_name = "python"
        elif file_name.endswith(".m"):
            CURRENT_LANGUAGE = MATLAB_LANGUAGE
            language_name = "matlab"
        elif file_name.endswith(".c"):
            CURRENT_LANGUAGE = C_LANGUAGE
            language_name = "c"
        elif file_name.endswith(".java"):
            CURRENT_LANGUAGE = JAVA_LANGUAGE
            language_name = "java"
        else:
            continue

        parser = Parser(CURRENT_LANGUAGE)
        tree = parser.parse(file_data, encoding='utf8')

        pattern_cur.execute(
            "SELECT id, title, regex_string, code_string, text, short_text, kind, on_match, citation," +\
            "severity, description from pattern where LOWER(language)=? and version=? and is_disabled=0",
            (language_name,7,)
        )

        for (pattern_id, pattern_name, query_string, code_string, pattern_text, pattern_short_text, pattern_kind,\
                pattern_on_match, pattern_citation, pattern_severity, pattern_description) in pattern_cur:
            query = CURRENT_LANGUAGE.query(query_string)
            matches = query.matches(tree.root_node)

            add_no_match = False

            if len(matches) > 0:
                if query_code is not None:
                    # Create an arg list
                    args = query_code[query_code.index('(') + 1:query_code.index(')')]
                    args = [s.strip() for s in args.split(',')]
                    args = args[1:]

                    exec(query_code)

                    for match in matches:
                        func_call = 'antipattern(tree, '
                            
                        for i, arg in enumerate(args):
                            func_call += "match[1]['" + args[i] + "']"
                            if i < len(args) - 1:
                                func_call += ', '
                        func_call += ')'
                        eval_result = eval(func_call)
                        result = {}
                        if isinstance(eval_result, bool):
                            if (eval_result and pattern_on_match):
                                critique = {}
                                critique["start_line"] = match[1]['antipattern'][0].start_point[0] + 1
                                critique["start_column"] = match[1]['antipattern'][0].start_point[1] + 1
                                critique["start_position"] = 0
                                critique["end_line"] = match[1]['antipattern'][0].end_point[0] + 1
                                critique["end_column"] = match[1]['antipattern'][0].end_point[1] + 1
                                critique["end_position"] = 0
                                critique["issue_kind"] = pattern_severity
                                critique["issue_source"] = "",
                                critique["critique_item_type"] = "PARSE_TIME"
                                critique["text"] = pattern_text
                                critique["patternid"] = pattern_id
                                critique["is_native_method"] = 0
                                critique["submission_file_id"] = file_id
                                critique["severity"] = pattern_severity
                                critique["name"] = pattern_name
                                critique["priority"] = 0
                                critique["status"] = pattern_severity
                                critique["alt_text"] = pattern_short_text
                                critique["issue_type"] = pattern_severity
                                critique["description"] = pattern_description
                                critiques.append(critique)
                            elif (not eval_result and not pattern_on_match):
                                add_no_match = True
                            else:
                                main_critique["num_pass"] += 1

                        else:
                            if (eval_result[0] and pattern_on_match):
                                critique = {}
                                critique["start_line"] = min(eval_result[1])
                                critique["start_column"] = 0
                                critique["start_position"] = 0
                                critique["end_line"] = max(eval_result[1])
                                critique["end_column"] = 0
                                critique["end_position"] = 0
                                critique["issue_kind"] = pattern_severity
                                critique["issue_source"] = "",
                                critique["critique_item_type"] = "PARSE_TIME"
                                critique["text"] = pattern_text
                                critique["patternid"] = pattern_id
                                critique["is_native_method"] = 0
                                critique["submission_file_id"] = file_id
                                critique["severity"] = pattern_severity
                                critique["name"] = pattern_name
                                critique["priority"] = 0
                                critique["status"] = pattern_severity
                                critique["alt_text"] = pattern_short_text
                                critique["issue_type"] = pattern_severity
                                critique["description"] = pattern_description
                                critiques.append(critique)
                            elif (not eval_result[0] and not pattern_on_match):
                                add_no_match = True
                            else:
                                main_critique["num_pass"] += 1

                else:
                    if pattern_on_match:
                        for match in matches:
                            critique = {}
                            critique["start_line"] = match[1]['antipattern'][0].start_point[0] + 1
                            critique["start_column"] = match[1]['antipattern'][0].start_point[1] + 1
                            critique["start_position"] = 0
                            critique["end_line"] = match[1]['antipattern'][0].end_point[0] + 1
                            critique["end_column"] = match[1]['antipattern'][0].end_point[1] + 1
                            critique["end_position"] = 0
                            critique["issue_kind"] = pattern_severity
                            critique["issue_source"] = "",
                            critique["critique_item_type"] = "PARSE_TIME"
                            critique["text"] = pattern_text
                            critique["patternid"] = pattern_id
                            critique["is_native_method"] = 0
                            critique["submission_file_id"] = file_id
                            critique["severity"] = pattern_severity
                            critique["name"] = pattern_name
                            critique["priority"] = 0
                            critique["status"] = pattern_severity
                            critique["alt_text"] = pattern_short_text
                            critique["issue_type"] = pattern_severity
                            critique["description"] = pattern_description
                            critiques.append(critique)
                    else:
                        main_critique["num_pass"] += 1

            elif len(matches) == 0 and not pattern_on_match:
                add_no_match = True

            if add_no_match:
                critique = {}
                critique["start_line"] = 0
                critique["start_column"] = 0
                critique["start_position"] = 0
                critique["end_line"] = 0
                critique["end_column"] = 0
                critique["end_position"] = 0
                critique["issue_kind"] = pattern_severity
                critique["issue_source"] = "",
                critique["critique_item_type"] = "PARSE_TIME"
                critique["text"] = pattern_text
                critique["patternid"] = pattern_id
                critique["is_native_method"] = 0
                critique["submission_file_id"] = file_id
                critique["severity"] = pattern_severity
                critique["name"] = pattern_name
                critique["priority"] = 0
                critique["status"] = pattern_severity
                critique["alt_text"] = pattern_short_text
                critique["issue_type"] = pattern_severity
                critique["description"] = pattern_description
                critiques.append(critique)
                
                

    for critique in critiques:

        if critique["issue_kind"].lower() == "critical":
            main_critique["num_critical"] += 1
        else if critique["issue_kind"].lower() == "warning":
            main_critique["num_warning"] += 1

        assignment_cur.execute(
            "INSERT INTO critique_item(version, start_column, start_position, " +\
            "column_num, date_created, issue_kind, line, last_updated, issue_source, " +\
            "critique_item_type, text, patternid, is_native_method, submission_file_id, " +\
            "start_line, severity, position, name, priority, critique_id, end_line, status, " +\
            "end_position, alt_text, issue_type, description, end_column) " +\
            "values(?, ?, ?, ?, NOW(), ?, ?, NOW(), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (7, critique["start_column"], critique["start_position"], critique["start_column"], critique["issue_kind"],\
            critique["start_line"], critique["issue_source"], critique["critique_item_type"], critique["text"],\
            critique["patternid"], critique["is_native_method"], critique["submission_file_id"], critique["start_line"],\
            critique["severity"], critique["start_position"], critique["name"], critique["priority"], main_critique["id"],\
            critique["end_line"], critique["status"], critique["end_position"], critique["alt_text"], critique["issue_type"],\
            critique["description"], critique["end_column"],)
        )

        assignment_conn.commit()

    assignment_cur.execute(
        "UPDATE critique SET num_pass=?, num_critical=?, num_warning=? where id=?",
        (main_critique["num_pass"], main_critique["num_critical"], main_critique["num_warning"], main_critique["id"],)
    )

    assignment_conn.commit()

    print(len(critiques))
    return 0        


def main():
    if len(sys.argv) != 3:
        print("Usage: python astmatch.py <mode> <id>")
        return -1

    if sys.argv[1] != "test" and sys.argv[1] != "grade":
        print("Invalid mode! Use test or grade.")
        return -1

    parser = Parser(CURRENT_LANGUAGE)

    try:
        pattern_conn = mariadb.connect(
            user=SQL_USER,
            password=SQL_PASSWORD,
            host="localhost",
            port=3306,
            database="patterndb"
        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        return -1

    if sys.argv[1] == "test":
        return test(pattern_conn, sys.argv[2])
    else if sys.argv[1] == "grade":
        return grade(pattern_conn, sys.argv[2])

if __name__ == '__main__':
    main()
