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

#ifndef EXPR_H_
#define EXPR_H_

#include <string>
#include <vector>

#include "string_piece.h"

using namespace std;

class Evaluator;
struct Loc;

class Evaluable {
 public:
  virtual void Eval(Evaluator* ev, string* s) const = 0;
  string Eval(Evaluator*) const;

  virtual string substOneLevel(Evaluator*ev) const { (void)ev; return string("undef"); };
  virtual bool isVarRef() const { return false; };

 protected:
  Evaluable();
  virtual ~Evaluable();
};

class Value : public Evaluable {
 public:
  // All NewExpr calls take ownership of the Value instances.
  static Value *NewExpr(Value *v1, Value *v2);
  static Value *NewExpr(Value *v1, Value *v2, Value *v3);
  static Value *NewExpr(vector<Value *> *values);

  static Value *NewLiteral(StringPiece s);
  virtual ~Value();
  virtual bool IsLiteral() const { return false; }
  // Only safe after IsLiteral() returns true.
  virtual StringPiece GetLiteralValueUnsafe() const { return ""; }

  static string DebugString(const Value *);

 protected:
  Value();
  virtual string DebugString_() const = 0;
};

enum struct ParseExprOpt {
  NORMAL = 0,
  DEFINE,
  COMMAND,
  FUNC,
};

Value* ParseExprImpl(const Loc& loc,
                     StringPiece s,
                     const char* terms,
                     ParseExprOpt opt,
                     size_t* index_out,
                     bool trim_right_space = false);
Value* ParseExpr(const Loc& loc,
                 StringPiece s,
                 ParseExprOpt opt = ParseExprOpt::NORMAL);

string JoinValues(const vector<Value*>& vals, const char* sep);

void init_product_var_list(void);

#endif  // EXPR_H_
