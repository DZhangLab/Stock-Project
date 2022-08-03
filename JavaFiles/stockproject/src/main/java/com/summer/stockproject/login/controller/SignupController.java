package com.summer.stockproject.login.controller;

import com.summer.stockproject.login.Entity.User;
import com.summer.stockproject.login.service.UserServiceImpl;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/signup")
public class SignupController {

    private UserServiceImpl userServiceImpl;

    @Autowired
    public SignupController(UserServiceImpl userServiceImpl) {
        this.userServiceImpl = userServiceImpl;
    }

    @GetMapping()
    public String signupView() {
        return "login/signup";
    }

    @PostMapping()
    public String signup(@ModelAttribute User user) {
        if (userServiceImpl.doesUserExist(user.getEmail())) {
            return "exist";
        }

        userServiceImpl.save(user);

        return "redirect:/";
    }
}
