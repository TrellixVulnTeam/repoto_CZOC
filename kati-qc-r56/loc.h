// Copyright 2015 Google Inc. All rights reserved
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef LOC_H_
#define LOC_H_

#include <string>
#include <sstream>

#include "stringprintf.h"

struct Loc {
  Loc() : filename(0), lineno(-1) {}
  Loc(const char* f, int l) : filename(f), lineno(l) {}

  const char* filename;
  int lineno;
  
  string as_string() const {
    stringstream m;
    m << (filename?filename:"<undef>") << ":" << lineno;
    return m.str();
  }
};

#define LOCF(x) (x).filename, (x).lineno

#endif  // LOC_H_
