employee_data = """
@prefix ex: <http://example.com/> .


########################################################
# DEPARTMENTS
########################################################

ex:Engineering
    a ex:Department .

ex:HR
    a ex:Department .


########################################################
# ALICE
########################################################

ex:Alice
    a ex:Developer ;

    ex:worksIn ex:Engineering ;

    ex:manager ex:Bob .


########################################################
# BOB
########################################################

ex:Bob
    a ex:Manager ;

    ex:worksIn ex:HR ;

    ex:manager ex:Carol .


########################################################
# CAROL
########################################################

ex:Carol
    a ex:Employee ;

    ex:worksIn ex:HR ;

    ex:manager ex:Bob .
"""