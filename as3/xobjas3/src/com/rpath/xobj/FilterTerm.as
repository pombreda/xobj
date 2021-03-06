/*
# Copyright (c) 2008-2010 rPath, Inc.
#
# This program is distributed under the terms of the MIT License as found
# in a file called LICENSE. If it is not present, the license
# is always available at http://www.opensource.org/licenses/mit-license.php.
#
# This program is distributed in the hope that it will be useful, but
# without any warranty; without even the implied warranty of merchantability
# or fitness for a particular purpose. See the MIT License for full details.
#
*/

package com.rpath.xobj
{

[RemoteClass]
[Bindable]
public class FilterTerm
{
    public function FilterTerm(field:String,
                               value:String,
                               operator:String = EQUAL)
    {
        super();
        
        this.field = field;
        this.operator = operator;
        this.value = value;
    }
    
    /**
     * The field/property to filter on (LHS)
     */
    public var field:String;
    
    /**
     * The logical operator to apply (see static consts below)
     */
    public var operator:String;
    
    /**
     * The value to test the field against (RHS)
     */
    public var value:String;
    
    public static const EQUAL:String = "EQUAL";
    public static const NOT_EQUAL:String = "NOT_EQUAL";
    
    public static const IS_NULL:String = "IS_NULL";
    public static const IS_NOT_NULL:String = "IS_NOT_NULL";
    
    public static const LESS_THAN:String = "LESS_THAN";
    public static const LESS_THAN_OR_EQUAL:String = "LESS_THAN_OR_EQUAL";
    public static const GREATER_THAN:String = "GREATER_THAN";
    public static const GREATER_THAN_OR_EQUAL:String = "GREATER_THAN_OR_EQUAL";
    public static const LIKE:String = "LIKE";
    public static const NOT_LIKE:String = "NOT_LIKE";
    public static const IN:String = "IN";
    public static const NOT_IN:String = "NOT_IN";
/*  NOT YET IMPLEMENTED  
    public static const MATCHING:String = "MATCHING";
    public static const NOT_MATCHING:String = "NOT_MATCHING";
*/    
    public static const YES:String = "YES";
    public static const NO:String = "NO";
    
    
}
}