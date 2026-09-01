shapes = """
@prefix ex: <http://example.com/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .


########################################################
# EMPLOYEE SHAPE
########################################################

ex:EmployeeShape
    a sh:NodeShape ;

    sh:targetClass ex:Employee ;


    ####################################################
    # Rule 1:
    # Employee works in exactly one Department
    ####################################################

    sh:property [

        sh:path ex:worksIn ;

        sh:minCount 1 ;
        sh:maxCount 1 ;

        sh:class ex:Department ;

        sh:message
            "An employee must work in exactly one Department."
    ] ;


    ####################################################
    # Rule 2 and 3:
    # Exactly one manager
    # Manager must be Employee
    ####################################################

    sh:property [

        sh:path ex:manager ;

        sh:minCount 1 ;
        sh:maxCount 1 ;

        sh:class ex:Employee ;

        sh:message
            "An employee must have exactly one manager who is an Employee."
    ] ;


    ####################################################
    # Rule 4:
    # Employee cannot be own manager
    ####################################################

    sh:sparql [

        a sh:SPARQLConstraint ;

        sh:message
            "An employee cannot be their own manager." ;

        sh:select '''

            PREFIX ex: <http://example.com/>

            SELECT $this
            WHERE {

                $this ex:manager $this .

            }

        '''
    ] ;


    ####################################################
    # Rule 5:
    # Employee and manager must work in same department
    ####################################################

    sh:sparql [

        a sh:SPARQLConstraint ;

        sh:message
            "Employee and manager must work in the same department." ;

        sh:select '''

            PREFIX ex: <http://example.com/>

            SELECT $this
            WHERE {

                $this
                    ex:worksIn ?employeeDepartment ;
                    ex:manager ?manager .

                ?manager
                    ex:worksIn ?managerDepartment .

                FILTER(
                    ?employeeDepartment != ?managerDepartment
                )

            }

        '''
    ] .
"""


