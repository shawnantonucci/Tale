"""
Unittests for the driver

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import unittest
import heapq
import tale.driver as driver
import tale.globals
import tale.cmds.normal
import tale.cmds.wizard


class TestDriver(unittest.TestCase):
    def testAttributes(self):
        d = driver.Driver()
        self.assertEqual({}, d.state)
        self.assertEqual({}, tale.globals.mud_context.state)
        self.assertTrue(tale.globals.mud_context.state is d.state)
        self.assertEqual(d, tale.globals.mud_context.driver)


class TestDeferreds(unittest.TestCase):
    def testSortable(self):
        d1 = driver.Deferred(5, "owner", "callable", None, None)
        d2 = driver.Deferred(2, "owner", "callable", None, None)
        d3 = driver.Deferred(4, "owner", "callable", None, None)
        d4 = driver.Deferred(1, "owner", "callable", None, None)
        d5 = driver.Deferred(3, "owner", "callable", None, None)
        deferreds = sorted([d1, d2, d3, d4, d5])
        dues = [d.due for d in deferreds]
        self.assertEqual([1, 2, 3, 4, 5], dues)

    def testHeapq(self):
        d1 = driver.Deferred(5, "owner", "callable", None, None)
        d2 = driver.Deferred(2, "owner", "callable", None, None)
        d3 = driver.Deferred(4, "owner", "callable", None, None)
        d4 = driver.Deferred(1, "owner", "callable", None, None)
        d5 = driver.Deferred(3, "owner", "callable", None, None)
        heap = [d1, d2, d3, d4, d5]
        heapq.heapify(heap)
        dues = []
        while heap:
            dues.append(heapq.heappop(heap).due)
        self.assertEqual([1, 2, 3, 4, 5], dues)


class TestCommand(unittest.TestCase):
    def testCommandsLoaded(self):
        self.assertGreater(len(tale.cmds.normal.all_commands), 1)
        self.assertGreater(len(tale.cmds.wizard.all_commands), 1)

    def testEnableNotifyActionSet(self):
        for cmd in tale.cmds.normal.all_commands.values():
            self.assertIsNotNone(cmd.__doc__)
            self.assertTrue(cmd.enable_notify_action in (True, False))
        for cmd in tale.cmds.wizard.all_commands.values():
            self.assertIsNotNone(cmd.__doc__)
            self.assertFalse(cmd.enable_notify_action, "all wizard commands must have enable_notify_action set to False")


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
