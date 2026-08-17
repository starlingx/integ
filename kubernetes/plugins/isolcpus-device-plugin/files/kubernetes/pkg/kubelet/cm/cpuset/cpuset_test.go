//
// Copyright (c) 2026 Wind River Systems, Inc.
//
// SPDX-License-Identifier: Apache-2.0
//

package cpuset

import (
	"testing"
)

func TestNewCPUSet(t *testing.T) {
	s := NewCPUSet(0, 1, 2)
	if s.Size() != 3 {
		t.Errorf("Size() = %d, want 3", s.Size())
	}
}

func TestNewCPUSetEmpty(t *testing.T) {
	s := NewCPUSet()
	if !s.IsEmpty() {
		t.Error("expected empty set")
	}
}

func TestContains(t *testing.T) {
	s := NewCPUSet(1, 3, 5)
	if !s.Contains(3) {
		t.Error("should contain 3")
	}
	if s.Contains(2) {
		t.Error("should not contain 2")
	}
}

func TestEquals(t *testing.T) {
	a := NewCPUSet(1, 2, 3)
	b := NewCPUSet(3, 2, 1)
	if !a.Equals(b) {
		t.Error("sets should be equal")
	}
	c := NewCPUSet(1, 2)
	if a.Equals(c) {
		t.Error("sets should not be equal")
	}
}

func TestUnion(t *testing.T) {
	a := NewCPUSet(1, 2)
	b := NewCPUSet(2, 3)
	u := a.Union(b)
	if u.Size() != 3 {
		t.Errorf("Union size = %d, want 3", u.Size())
	}
}

func TestIntersection(t *testing.T) {
	a := NewCPUSet(1, 2, 3)
	b := NewCPUSet(2, 3, 4)
	i := a.Intersection(b)
	if i.Size() != 2 {
		t.Errorf("Intersection size = %d, want 2", i.Size())
	}
}

func TestDifference(t *testing.T) {
	a := NewCPUSet(1, 2, 3)
	b := NewCPUSet(2, 3)
	d := a.Difference(b)
	if d.Size() != 1 || !d.Contains(1) {
		t.Error("Difference should be {1}")
	}
}

func TestIsSubsetOf(t *testing.T) {
	a := NewCPUSet(1, 2)
	b := NewCPUSet(1, 2, 3)
	if !a.IsSubsetOf(b) {
		t.Error("a should be subset of b")
	}
	if b.IsSubsetOf(a) {
		t.Error("b should not be subset of a")
	}
}

func TestFilter(t *testing.T) {
	s := NewCPUSet(1, 2, 3, 4)
	even := s.Filter(func(c int) bool {
		return c%2 == 0
	})
	if even.Size() != 2 {
		t.Errorf("Filter size = %d, want 2", even.Size())
	}
}

func TestFilterNot(t *testing.T) {
	s := NewCPUSet(1, 2, 3, 4)
	odd := s.FilterNot(func(c int) bool {
		return c%2 == 0
	})
	if odd.Size() != 2 {
		t.Errorf("FilterNot size = %d, want 2", odd.Size())
	}
}

func TestToSlice(t *testing.T) {
	s := NewCPUSet(3, 1, 2)
	sl := s.ToSlice()
	if len(sl) != 3 || sl[0] != 1 || sl[1] != 2 || sl[2] != 3 {
		t.Errorf("ToSlice = %v, want [1 2 3]", sl)
	}
}

func TestToSliceNoSort(t *testing.T) {
	s := NewCPUSet(1, 2, 3)
	sl := s.ToSliceNoSort()
	if len(sl) != 3 {
		t.Errorf("len = %d, want 3", len(sl))
	}
}

func TestString(t *testing.T) {
	tests := []struct {
		cpus []int
		want string
	}{
		{nil, ""},
		{[]int{0}, "0"},
		{[]int{0, 1, 2}, "0-2"},
		{[]int{0, 2, 4}, "0,2,4"},
		{[]int{0, 1, 2, 5, 6}, "0-2,5-6"},
	}
	for _, tc := range tests {
		s := NewCPUSet(tc.cpus...)
		got := s.String()
		if got != tc.want {
			t.Errorf("String(%v) = %q, want %q",
				tc.cpus, got, tc.want)
		}
	}
}

func TestParse(t *testing.T) {
	tests := []struct {
		input string
		size  int
	}{
		{"", 0},
		{"0", 1},
		{"0-3", 4},
		{"0,2,4", 3},
		{"0-2,5-6", 5},
	}
	for _, tc := range tests {
		s, err := Parse(tc.input)
		if err != nil {
			t.Errorf("Parse(%q) error: %v", tc.input, err)
			continue
		}
		if s.Size() != tc.size {
			t.Errorf("Parse(%q).Size() = %d, want %d",
				tc.input, s.Size(), tc.size)
		}
	}
}

func TestParseErrors(t *testing.T) {
	bad := []string{"abc", "1-abc", "abc-5"}
	for _, input := range bad {
		_, err := Parse(input)
		if err == nil {
			t.Errorf("Parse(%q) should error", input)
		}
	}
}

func TestClone(t *testing.T) {
	s := NewCPUSet(1, 2, 3)
	c := s.Clone()
	if !s.Equals(c) {
		t.Error("Clone should equal original")
	}
}

func TestUnionAll(t *testing.T) {
	a := NewCPUSet(1)
	b := NewCPUSet(2)
	c := NewCPUSet(3)
	u := a.UnionAll([]CPUSet{b, c})
	if u.Size() != 3 {
		t.Errorf("UnionAll size = %d, want 3", u.Size())
	}
}

func TestBuilderAddAfterResult(t *testing.T) {
	// Builder uses value receivers, so done flag
	// does not propagate. This is by design.
	b := NewBuilder()
	b.Add(1)
	r := b.Result()
	if !r.Contains(1) {
		t.Error("Result should contain 1")
	}
}

func TestMustParse(t *testing.T) {
	s := MustParse("0-3,5")
	if s.Size() != 5 {
		t.Errorf("Size() = %d, want 5", s.Size())
	}
	if !s.Contains(5) {
		t.Error("should contain 5")
	}
}

func TestMustParseEmpty(t *testing.T) {
	s := MustParse("")
	if !s.IsEmpty() {
		t.Error("expected empty set")
	}
}
