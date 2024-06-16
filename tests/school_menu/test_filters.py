from school_menu.templatetags import filters


class TestTruncateFilter:
    def testinputlongerthanmax(self):
        assert filters.truncate("hello", 3) == "hel"

    def testinputshorterthanmax(self):
        assert filters.truncate("hello", 10) == "hello"


class TestWeeksFilter:
    def testrandominput(self):
        assert filters.weeks(3) == range(1, 4)
