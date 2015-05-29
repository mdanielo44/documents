# -*- coding: utf-8 -*-
'''
lucterios.contacts package

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2015 sd-libre.fr
@license: This file is part of Lucterios.

Lucterios is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Lucterios is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Lucterios.  If not, see <http://www.gnu.org/licenses/>.
'''

from __future__ import unicode_literals
from lucterios.framework.test import LucteriosTest, add_empty_user
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from unittest.suite import TestSuite
from unittest.loader import TestLoader
from lucterios.documents.views import FolderList, FolderAddModify, FolderDel, \
    DocumentList, DocumentAddModify, DocumentShow, DocumentDel
from lucterios.CORE.models import LucteriosGroup, LucteriosUser
from lucterios.documents.models import Folder, Document
from os.path import join, dirname, exists
from lucterios.framework.filetools import get_user_path, get_user_dir
from shutil import rmtree, copyfile
from django.utils import formats, timezone

class FolderTest(LucteriosTest):
    # pylint: disable=too-many-public-methods,too-many-statements

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        group = LucteriosGroup.objects.create(name="my_group")  # pylint: disable=no-member
        group.save()
        group = LucteriosGroup.objects.create(name="other_group")  # pylint: disable=no-member
        group.save()

    def test_list(self):
        self.factory.xfer = FolderList()
        self.call('/lucterios.documents/folderList', {}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'folderList')
        self.assert_xml_equal('TITLE', 'Dossiers')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('ACTIONS/ACTION', 1)
        self.assert_action_equal('ACTIONS/ACTION', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 4)
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="folder"]', (0, 1, 2, 1))
        self.assert_count_equal('COMPONENTS/GRID[@name="folder"]/HEADER', 3)
        self.assert_xml_equal('COMPONENTS/GRID[@name="folder"]/HEADER[@name="name"]', "nom")
        self.assert_xml_equal('COMPONENTS/GRID[@name="folder"]/HEADER[@name="description"]', "description")
        self.assert_xml_equal('COMPONENTS/GRID[@name="folder"]/HEADER[@name="parent"]', "parent")
        self.assert_count_equal('COMPONENTS/GRID[@name="folder"]/RECORD', 0)

    def test_add(self):
        self.factory.xfer = FolderAddModify()
        self.call('/lucterios.documents/folderAddModify', {}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'folderAddModify')
        self.assert_xml_equal('TITLE', 'Ajouter un dossier')
        self.assert_count_equal('COMPONENTS/*', 27)
        self.assert_comp_equal('COMPONENTS/EDIT[@name="name"]', None, (1, 0, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/MEMO[@name="description"]', None, (1, 1, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/SELECT[@name="parent"]', '0', (1, 2, 1, 1, 1))
        self.assert_count_equal('COMPONENTS/SELECT[@name="parent"]/CASE', 1)
        self.assert_coordcomp_equal('COMPONENTS/CHECKLIST[@name="viewer_available"]', (1, 1, 1, 5, 2))
        self.assert_coordcomp_equal('COMPONENTS/CHECKLIST[@name="viewer_chosen"]', (3, 1, 1, 5, 2))
        self.assert_coordcomp_equal('COMPONENTS/CHECKLIST[@name="modifier_available"]', (1, 6, 1, 5, 2))
        self.assert_coordcomp_equal('COMPONENTS/CHECKLIST[@name="modifier_chosen"]', (3, 6, 1, 5, 2))

    def test_addsave(self):

        folder = Folder.objects.all()  # pylint: disable=no-member
        self.assertEqual(len(folder), 0)

        self.factory.xfer = FolderAddModify()
        self.call('/lucterios.documents/folderAddModify', {'SAVE':'YES', 'name':'newcat', 'description':'new folder', \
                                       'parent':'0', 'viewer':'1;2', 'modifier':'2'}, False)
        self.assert_observer('Core.Acknowledge', 'lucterios.documents', 'folderAddModify')
        self.assert_count_equal('CONTEXT/PARAM', 6)

        folder = Folder.objects.all()  # pylint: disable=no-member
        self.assertEqual(len(folder), 1)
        self.assertEqual(folder[0].name, "newcat")
        self.assertEqual(folder[0].description, "new folder")
        self.assertEqual(folder[0].parent, None)
        grp = folder[0].viewer.all().order_by('id')  # pylint: disable=no-member
        self.assertEqual(len(grp), 2)
        self.assertEqual(grp[0].id, 1)
        self.assertEqual(grp[1].id, 2)
        grp = folder[0].modifier.all().order_by('id')  # pylint: disable=no-member
        self.assertEqual(len(grp), 1)
        self.assertEqual(grp[0].id, 2)

        self.factory.xfer = FolderList()
        self.call('/lucterios.documents/folderList', {}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'folderList')
        self.assert_count_equal('COMPONENTS/GRID[@name="folder"]/RECORD', 1)

    def test_delete(self):
        folder = Folder.objects.create(name='truc', description='blabla')  # pylint: disable=no-member
        folder.viewer = LucteriosGroup.objects.filter(id__in=[1, 2])  # pylint: disable=no-member
        folder.modifier = LucteriosGroup.objects.filter(id__in=[2])  # pylint: disable=no-member
        folder.save()

        self.factory.xfer = FolderList()
        self.call('/lucterios.documents/folderList', {}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'folderList')
        self.assert_count_equal('COMPONENTS/GRID[@name="folder"]/RECORD', 1)

        self.factory.xfer = FolderDel()
        self.call('/lucterios.documents/folderDel', {'folder':'1', "CONFIRME":'YES'}, False)
        self.assert_observer('Core.Acknowledge', 'lucterios.documents', 'folderDel')

        self.factory.xfer = FolderList()
        self.call('/lucterios.documents/folderList', {}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'folderList')
        self.assert_count_equal('COMPONENTS/GRID[@name="folder"]/RECORD', 0)

class DocumentTest(LucteriosTest):
    # pylint: disable=too-many-public-methods,too-many-statements

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        rmtree(get_user_dir(), True)
        current_user = add_empty_user()
        current_user.is_superuser = True
        current_user.save()

        group = LucteriosGroup.objects.create(name="my_group")  # pylint: disable=no-member
        group.save()
        group = LucteriosGroup.objects.create(name="other_group")  # pylint: disable=no-member
        group.save()
        folder1 = Folder.objects.create(name='truc1', description='blabla')  # pylint: disable=no-member
        folder1.viewer = LucteriosGroup.objects.filter(id__in=[1, 2])  # pylint: disable=no-member
        folder1.modifier = LucteriosGroup.objects.filter(id__in=[2])  # pylint: disable=no-member
        folder1.save()
        folder2 = Folder.objects.create(name='truc2', description='bouuuuu!')  # pylint: disable=no-member
        folder2.viewer = LucteriosGroup.objects.filter(id__in=[2])  # pylint: disable=no-member
        folder2.modifier = LucteriosGroup.objects.filter(id__in=[2])  # pylint: disable=no-member
        folder2.save()
        folder3 = Folder.objects.create(name='truc3', description='----')  # pylint: disable=no-member
        folder3.parent = folder2
        folder3.save()

    def create_doc(self):
        self.factory.user = LucteriosUser.objects.get(username='empty')  # pylint: disable=no-member
        file_path = join(dirname(__file__), 'images', 'documentFind.png')
        copyfile(file_path, get_user_path('documents', 'document_1'))
        current_date = timezone.now()
        new_doc = Document.objects.create(name='doc.png', description="new doc", creator=self.factory.user, date_creation=current_date, date_modification=current_date) # pylint: disable=no-member
        new_doc.folder = Folder.objects.get(id=2) # pylint: disable=no-member
        new_doc.save()
        return current_date

    def test_list(self):
        folder = Folder.objects.all()  # pylint: disable=no-member
        self.assertEqual(len(folder), 3)

        self.factory.xfer = DocumentList()
        self.call('/lucterios.documents/documentList', {}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'documentList')
        self.assert_xml_equal('TITLE', 'Documents')
        self.assert_count_equal('CONTEXT', 0)
        self.assert_count_equal('ACTIONS/ACTION', 1)
        self.assert_action_equal('ACTIONS/ACTION', ('Fermer', 'images/close.png'))
        self.assert_count_equal('COMPONENTS/*', 9)
        self.assert_coordcomp_equal('COMPONENTS/GRID[@name="document"]', (2, 2, 2, 2))
        self.assert_count_equal('COMPONENTS/GRID[@name="document"]/HEADER', 4)
        self.assert_xml_equal('COMPONENTS/GRID[@name="document"]/HEADER[@name="name"]', "nom")
        self.assert_xml_equal('COMPONENTS/GRID[@name="document"]/HEADER[@name="description"]', "description")
        self.assert_xml_equal('COMPONENTS/GRID[@name="document"]/HEADER[@name="date_modification"]', "date de modification")
        self.assert_xml_equal('COMPONENTS/GRID[@name="document"]/HEADER[@name="modifier"]', "modificateur")
        self.assert_count_equal('COMPONENTS/GRID[@name="document"]/RECORD', 0)

        self.assert_coordcomp_equal('COMPONENTS/CHECKLIST[@name="current_folder"]', (0, 2, 2, 1))
        self.assert_count_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE', 2)
        self.assert_xml_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE[@id="1"]', "truc1")
        self.assert_xml_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE[@id="2"]', "truc2")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lbltitlecat"]', ">")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lbldesc"]', '{[center]}{[i]}{[/i]}{[/center]}')

        self.factory.xfer = DocumentList()
        self.call('/lucterios.documents/documentList', {"current_folder":"1"}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'documentList')
        self.assert_count_equal('COMPONENTS/GRID[@name="document"]/RECORD', 0)
        self.assert_count_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE', 1)
        self.assert_xml_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE[@id="0"]', "..")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lbltitlecat"]', ">truc1")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lbldesc"]', "{[center]}{[i]}blabla{[/i]}{[/center]}")

        self.factory.xfer = DocumentList()
        self.call('/lucterios.documents/documentList', {"current_folder":"2"}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'documentList')
        self.assert_count_equal('COMPONENTS/GRID[@name="document"]/RECORD', 0)
        self.assert_count_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE', 2)
        self.assert_xml_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE[@id="0"]', "..")
        self.assert_xml_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE[@id="3"]', "truc3")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lbltitlecat"]', ">truc2")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lbldesc"]', "{[center]}{[i]}bouuuuu!{[/i]}{[/center]}")

        self.factory.xfer = DocumentList()
        self.call('/lucterios.documents/documentList', {"current_folder":"3"}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'documentList')
        self.assert_count_equal('COMPONENTS/GRID[@name="document"]/RECORD', 0)
        self.assert_count_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE', 1)
        self.assert_xml_equal('COMPONENTS/CHECKLIST[@name="current_folder"]/CASE[@id="2"]', "..")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lbltitlecat"]', ">truc2>truc3")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="lbldesc"]', "{[center]}{[i]}----{[/i]}{[/center]}")

    def test_add(self):
        self.factory.xfer = DocumentAddModify()
        self.call('/lucterios.documents/documentAddModify', {"current_folder":"2"}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'documentAddModify')
        self.assert_xml_equal('TITLE', 'Ajouter un document')
        self.assert_count_equal('COMPONENTS/*', 7)
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="folder"]', ">truc2", (2, 0, 1, 1))
        self.assert_comp_equal('COMPONENTS/UPLOAD[@name="filename"]', None, (2, 1, 1, 1))
        self.assert_comp_equal('COMPONENTS/MEMO[@name="description"]', None, (2, 2, 1, 1))

    def test_addsave(self):
        self.factory.user = LucteriosUser.objects.get(username='empty')  # pylint: disable=no-member

        self.assertFalse(exists(get_user_path('documents', 'document_1')))
        file_path = join(dirname(__file__), 'images', 'documentFind.png')

        docs = Document.objects.all()  # pylint: disable=no-member
        self.assertEqual(len(docs), 0)

        self.factory.xfer = DocumentAddModify()
        with open(file_path, 'rb') as file_to_load:
            self.call('/lucterios.documents/documentAddModify', {"current_folder":"2", 'SAVE':'YES', 'description':'new doc', \
                        'filename_FILENAME':'doc.png', 'filename':file_to_load}, False)
        self.assert_observer('Core.Acknowledge', 'lucterios.documents', 'documentAddModify')
        self.assert_count_equal('CONTEXT/PARAM', 4)

        docs = Document.objects.all()  # pylint: disable=no-member
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].folder.id, 2)
        self.assertEqual(docs[0].name, 'doc.png')
        self.assertEqual(docs[0].description, "new doc")
        self.assertEqual(docs[0].creator.username, "empty")
        self.assertEqual(docs[0].modifier.username, "empty")
        self.assertEqual(docs[0].date_creation, docs[0].date_modification)
        self.assertTrue(exists(get_user_path('documents', 'document_1')))

    def test_saveagain(self):
        current_date = self.create_doc()

        self.factory.xfer = DocumentShow()
        self.call('/lucterios.documents/documentShow', {"document":"1"}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'documentShow')
        self.assert_xml_equal('TITLE', 'Voir un document')
        self.assert_count_equal('COMPONENTS/*', 16)
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="folder"]', ">truc2", (2, 0, 3, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="name"]', "doc.png", (2, 1, 3, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="description"]', "new doc", (2, 2, 3, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="modifier"]', '---', (2, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="date_modification"]', formats.date_format(current_date, "DATETIME_FORMAT"), (4, 3, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="creator"]', "empty", (2, 4, 1, 1))
        self.assert_comp_equal('COMPONENTS/LABELFORM[@name="date_creation"]', formats.date_format(current_date, "DATETIME_FORMAT"), (4, 4, 1, 1))

        self.factory.xfer = DocumentAddModify()
        self.call('/lucterios.documents/documentAddModify', {'SAVE':'YES', "document":"1", 'description':'old doc'}, False)
        docs = Document.objects.all()  # pylint: disable=no-member
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].folder.id, 2)
        self.assertEqual(docs[0].name, 'doc.png')
        self.assertEqual(docs[0].description, "old doc")
        self.assertEqual(docs[0].creator.username, "empty")
        self.assertEqual(docs[0].modifier.username, "empty")
        self.assertNotEqual(docs[0].date_creation, docs[0].date_modification)

    def test_delete(self):
        current_date = self.create_doc()

        self.factory.xfer = DocumentList()
        self.call('/lucterios.documents/documentList', {"current_folder":"2"}, False)
        self.assert_observer('Core.Custom', 'lucterios.documents', 'documentList')
        self.assert_count_equal('COMPONENTS/GRID[@name="document"]/RECORD', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="document"]/RECORD[@id="1"]/VALUE[@name="name"]', "doc.png")
        self.assert_xml_equal('COMPONENTS/GRID[@name="document"]/RECORD[@id="1"]/VALUE[@name="description"]', "new doc")
        self.assert_xml_equal('COMPONENTS/GRID[@name="document"]/RECORD[@id="1"]/VALUE[@name="date_modification"]', formats.date_format(current_date, "DATETIME_FORMAT"))
        self.assert_xml_equal('COMPONENTS/GRID[@name="document"]/RECORD[@id="1"]/VALUE[@name="modifier"]', "---")
        self.assertTrue(exists(get_user_path('documents', 'document_1')))

        self.factory.xfer = DocumentDel()
        self.call('/lucterios.documents/documentDel', {"document":"1", "CONFIRME":'YES'}, False)
        self.assert_observer('Core.Acknowledge', 'lucterios.documents', 'documentDel')

        self.factory.xfer = DocumentList()
        self.call('/lucterios.documents/documentList', {"current_folder":"2"}, False)
        self.assert_count_equal('COMPONENTS/GRID[@name="document"]/RECORD', 0)
        self.assertFalse(exists(get_user_path('documents', 'document_1')))

def suite():
    # pylint: disable=redefined-outer-name
    suite = TestSuite()
    loader = TestLoader()
    suite.addTest(loader.loadTestsFromTestCase(FolderTest))
    suite.addTest(loader.loadTestsFromTestCase(DocumentTest))
    return suite
