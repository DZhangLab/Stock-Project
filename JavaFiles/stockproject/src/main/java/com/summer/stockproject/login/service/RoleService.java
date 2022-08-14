package com.summer.stockproject.login.service;

import com.summer.stockproject.login.Entity.Role;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public interface RoleService {
    public List<Role> findAll();
}
