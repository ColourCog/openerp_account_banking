#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  uba_parser.py
#
#  Copyright 2015 Bidossessi Sodonon <bidossessi@linuxbenin.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#
import hashlib
from openerp.addons.account_banking.parsers import models
from openerp.addons.account_banking.parsers import convert

parser = models.parser
bs = models.mem_bank_statement
bt = models.mem_bank_transaction


class UBAParser(parser):
    '''
    A parser delivers the interface for any parser object. Inherit from
    it to implement your own.
    You should at least implement the following at the class level:
        name -> the name of the parser, shown to the user and
                    translatable.
        code -> the identifier you care to give it. Not translatable
        country_code -> the two letter ISO code of the country this parser is
                        built for: used to recreate country when new partners
                        are auto created
        doc  -> the description of the identifier. Shown to the user.
                    Translatable.

        parse -> the method for the actual parsing.
    '''
    name = "UBA Benin"
    code = "UBABJ"
    country_code = "BJ"
    doc = __doc__

    def parse(self, cr, data):
        '''
        Parse data.

        data is a raw in memory file object. You have to split it in
        whatever chunks you see fit for parsing. It should return a list
        of mem_bank_statement objects. Every mem_bank_statement object
        should contain a list of mem_bank_transaction objects.

        For identification purposes, don't invent numbering of the transaction
        numbers or bank statements ids on your own - stick with those provided
        by your bank. Doing so enables the users to re-load old transaction
        files without creating multiple identical bank statements.

        If your bank does not provide transaction ids, take a high resolution
        and a repeatable algorithm for the numbering. For example the date can
        be used as a prefix. Adding a tracer (day resolution) can create
        uniqueness. Adding unique statement ids can add to the robustness of
        your transaction numbering.

        Just mind that users can create random (file)containers with
        transactions in it. Try not to depend on order of appearance within
        these files. If in doubt: sort.
        '''
        statement = bs()
        lines = data.split('\n')
        last_balance = ''
        for line in lines:
            sp = line.split(';')
            # ignore empty lines
            if not bool(''.join(sp)):
                continue
            if sp[0] == '':
                if "Relevé de compte mensuel" in sp[1]:
                    statement.id = sp[1].split("du ")[1].capitalize()
                if "Numéro de compte :" in sp[1]:
                    statement.local_account = sp[1].split(":")[1].replace(' ','')
                continue
            if sp[0] == 'DATE':
                continue
            if sp[1] == "Solde reporté":
                statement.start_balance = convert.str2float(sp[7])
                continue
            d = bt()
            d.id = hashlib.md5(line).hexdigest()
            d.transfer_type = "DD"
            d.statement_id = statement.id
            d.local_account = statement.local_account
            d.execution_date = convert.str2date(sp[0], '%d-%b-%Y')
            d.message = sp[1]
            d.remote_account = "N/A in Statement"
            d.value_date = convert.str2date(sp[3], '%d-%b-%Y')
            d.reference = sp[2]
            if sp[4] and sp[4] != sp[2]:
                d.reference = sp[4]
            if "Droit de Timbre" in sp[1]:
                d.transfer_type = "BC"
            if "CERTIF" in sp[1]:
                d.transfer_type = "BC"
            if "SMS CHARGES" in sp[1]:
                d.transfer_type = "BC"
            if "COMM. MENSUELLES" in sp[1]:
                d.transfer_type = "BC"
            if sp[5]:
                d.transferred_amount = convert.str2float(sp[5], True)
            if sp[6]:
                d.transferred_amount = convert.str2float(sp[6])
            if sp[2] != '':
                d.transfer_type = "CK"
            last_balance = sp[7]
            last_date = sp[0]
            statement.transactions.append(d)
        statement.end_balance = convert.str2float(last_balance)
        statement.date = convert.str2date(last_date, '%d-%b-%Y')
        return [statement]
