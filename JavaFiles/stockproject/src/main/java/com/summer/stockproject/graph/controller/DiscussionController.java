package com.summer.stockproject.graph.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/discussion")
public class DiscussionController {

    @GetMapping("/board")
    public String showBoard() {

        return "discussion/board";
    }

    @GetMapping("/post")
    public String postDiscussion() {

        return "discussion/post";
    }
}
